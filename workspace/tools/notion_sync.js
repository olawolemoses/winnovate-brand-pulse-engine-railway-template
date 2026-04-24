#!/usr/bin/env node
import { Client as NotionClient } from "@notionhq/client";

class ToolError extends Error {
  constructor(message) {
    super(message);
    this.name = "ToolError";
  }
}

function formatIdPrefix(id) {
  return String(id || "").slice(0, 5) || "unset";
}

function logDatabaseFailure(label, databaseId, error) {
  console.error(
    `[notion_sync] ${label} failed for database prefix=${formatIdPrefix(databaseId)}: ${error.message}`
  );
}

function getNotionConfig() {
  const token = process.env.NOTION_TOKEN;
  const brandDbId = process.env.NOTION_BRAND_DB_ID;
  const pulseDbId = process.env.NOTION_PULSE_DB_ID;

  if (!token) {
    throw new ToolError("Missing NOTION_TOKEN environment variable.");
  }
  if (!brandDbId) {
    throw new ToolError("Missing NOTION_BRAND_DB_ID environment variable.");
  }
  if (!pulseDbId) {
    throw new ToolError("Missing NOTION_PULSE_DB_ID environment variable.");
  }

  return { token, brandDbId, pulseDbId };
}

function getClient() {
  const { token } = getNotionConfig();
  return new NotionClient({ auth: token });
}

async function upsertBrand(placeId, name) {
  if (!placeId || !String(placeId).trim()) {
    throw new ToolError("upsertBrand requires a placeId.");
  }
  if (!name || !String(name).trim()) {
    throw new ToolError("upsertBrand requires a name.");
  }

  const client = getClient();
  const { brandDbId } = getNotionConfig();

  try {
    const search = await client.databases.query({
      database_id: brandDbId,
      filter: {
        property: "Place ID",
        rich_text: {
          equals: String(placeId).trim(),
        },
      },
      page_size: 1,
    });

    if (search.results.length > 0) {
      return search.results[0].id;
    }
  } catch (error) {
    logDatabaseFailure("Brand lookup", brandDbId, error);
    throw new ToolError(`Brand upsert failed: ${error.message}`);
  }

  try {
    const created = await client.pages.create({
      parent: { database_id: brandDbId },
      properties: {
        Name: {
          title: [{ text: { content: String(name).trim() } }],
        },
        "Place ID": {
          rich_text: [{ text: { content: String(placeId).trim() } }],
        },
      },
    });

    return created.id;
  } catch (error) {
    logDatabaseFailure("Brand create", brandDbId, error);
    throw new ToolError(`Brand upsert failed: ${error.message}`);
  }
}

function normalizeCategorizedData(categorizedData) {
  if (!categorizedData || typeof categorizedData !== "object") {
    throw new ToolError("Categorized data must be a JSON object.");
  }
  if (categorizedData.ok === false) {
    throw new ToolError(categorizedData.error || "Categorized payload was marked as failed.");
  }

  return {
    place_id: categorizedData.place_id || "",
    place_name: categorizedData.place_name || "",
    praise_candidates: Array.isArray(categorizedData.praise_candidates) ? categorizedData.praise_candidates : [],
    friction_alerts: Array.isArray(categorizedData.friction_alerts) ? categorizedData.friction_alerts : [],
  };
}

function buildPulsePagePayload(item, type, brandPageId) {
  const content = type === "Praise" ? item.punchy_quote : item.trello_action_item;
  if (!content || !String(content).trim()) {
    throw new ToolError(`${type} item is missing its generated content field.`);
  }

  return {
    Content: {
      title: [{ text: { content: String(content).trim().slice(0, 2000) } }],
    },
    Type: {
      select: { name: type },
    },
    Status: {
      select: { name: "Pending" },
    },
    "Brand Registry": {
      relation: [{ id: brandPageId }],
    },
    "Review Rating": {
      number: typeof item.rating === "number" ? item.rating : null,
    },
    Author: {
      rich_text: item.author ? [{ text: { content: String(item.author).slice(0, 2000) } }] : [],
    },
    "Original Review": {
      rich_text: item.text ? [{ text: { content: String(item.text).slice(0, 2000) } }] : [],
    },
  };
}

async function syncPulseItems(categorizedData, brandPageId) {
  if (!brandPageId || !String(brandPageId).trim()) {
    throw new ToolError("syncPulseItems requires a brandPageId.");
  }

  const normalized = normalizeCategorizedData(categorizedData);
  const client = getClient();
  const { pulseDbId } = getNotionConfig();
  const results = {
    praise_count: 0,
    friction_count: 0,
    page_ids: [],
  };

  const createForItems = async (items, type) => {
    for (const item of items) {
      try {
        const created = await client.pages.create({
          parent: { database_id: pulseDbId },
          properties: buildPulsePagePayload(item, type, brandPageId),
        });
        results.page_ids.push(created.id);
        if (type === "Praise") {
          results.praise_count += 1;
        } else {
          results.friction_count += 1;
        }
      } catch (error) {
        logDatabaseFailure(`${type} sync`, pulseDbId, error);
        throw new ToolError(`Pulse sync failed for ${type.toLowerCase()} item: ${error.message}`);
      }
    }
  };

  await createForItems(normalized.praise_candidates, "Praise");
  await createForItems(normalized.friction_alerts, "Friction");

  return results;
}

function parseCliArgs(argv) {
  const args = argv.slice(2);
  const dataIndex = args.findIndex((arg) => arg === "--data");
  const placeIdIndex = args.findIndex((arg) => arg === "--place-id");
  const nameIndex = args.findIndex((arg) => arg === "--name");

  if (dataIndex === -1 || !args[dataIndex + 1]) {
    throw new ToolError("Usage: node workspace/tools/notion_sync.js --data '<JSON>' [--place-id PLACE_ID] [--name PLACE_NAME]");
  }

  let data;
  try {
    data = JSON.parse(args[dataIndex + 1]);
  } catch (error) {
    throw new ToolError(`Invalid JSON passed to --data: ${error.message}`);
  }

  return {
    data,
    placeId: placeIdIndex !== -1 ? args[placeIdIndex + 1] : undefined,
    name: nameIndex !== -1 ? args[nameIndex + 1] : undefined,
  };
}

async function main() {
  try {
    const { data, placeId, name } = parseCliArgs(process.argv);
    const normalized = normalizeCategorizedData(data);
    const resolvedPlaceId = placeId || normalized.place_id;
    const resolvedName = name || normalized.place_name;

    const brandPageId = await upsertBrand(resolvedPlaceId, resolvedName);
    const syncResult = await syncPulseItems(normalized, brandPageId);

    process.stdout.write(JSON.stringify({
      ok: true,
      brand_page_id: brandPageId,
      place_id: resolvedPlaceId,
      place_name: resolvedName,
      praise_count: syncResult.praise_count,
      friction_count: syncResult.friction_count,
      page_ids: syncResult.page_ids,
      summary: `Staged ${syncResult.praise_count} praise items and ${syncResult.friction_count} friction alerts in the Pulse Console.`,
    }));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    process.stdout.write(JSON.stringify({ ok: false, error: message }));
    process.exitCode = 1;
  }
}

export { upsertBrand, syncPulseItems };
await main();
