#!/usr/bin/env node
import { Client as NotionClient } from "@notionhq/client";

class ToolError extends Error {
  constructor(message) {
    super(message);
    this.name = "ToolError";
  }
}

function parseCliInput(argv) {
  const args = argv.slice(2);
  const jsonArgIndex = args.findIndex((arg) => arg === "--item");
  const routeArgIndex = args.findIndex((arg) => arg === "--route");
  const modeArgIndex = args.findIndex((arg) => arg === "--mode");

  if (jsonArgIndex === -1 || !args[jsonArgIndex + 1]) {
    throw new ToolError("Usage: node workspace/tools/action_dispatcher.js --item '<JSON>' [--route notion|trello|both] [--mode payload|url]");
  }

  let item;
  try {
    item = JSON.parse(args[jsonArgIndex + 1]);
  } catch (error) {
    throw new ToolError(`Invalid JSON passed to --item: ${error.message}`);
  }

  const route = routeArgIndex !== -1 && args[routeArgIndex + 1] ? args[routeArgIndex + 1] : "both";
  const mode = modeArgIndex !== -1 && args[modeArgIndex + 1] ? args[modeArgIndex + 1] : "payload";

  if (!["notion", "trello", "both"].includes(route)) {
    throw new ToolError("--route must be one of: notion, trello, both.");
  }

  if (!["payload", "url"].includes(mode)) {
    throw new ToolError("--mode must be one of: payload, url.");
  }

  return { item, route, mode };
}

function normalizeApprovedItem(rawItem) {
  if (!rawItem || typeof rawItem !== "object") {
    throw new ToolError("Approved item must be a JSON object.");
  }

  const placeName = rawItem.place_name || rawItem.placeName || "";
  const type = rawItem.type || rawItem.category || "";
  const content = rawItem.content || rawItem.punchy_quote || rawItem.trello_action_item || "";
  const status = rawItem.status || "Pending";

  if (!placeName.trim()) {
    throw new ToolError("Approved item is missing place_name.");
  }
  if (!type || !["Praise", "Friction"].includes(type)) {
    throw new ToolError("Approved item type must be Praise or Friction.");
  }
  if (!content.trim()) {
    throw new ToolError("Approved item is missing content, punchy_quote, or trello_action_item.");
  }
  if (!["Live", "Pending"].includes(status)) {
    throw new ToolError("Approved item status must be Live or Pending.");
  }

  return {
    place_name: placeName.trim(),
    type,
    content: content.trim(),
    status,
    source_review: rawItem,
  };
}

function getNotionConfig() {
  const apiKey = process.env.NOTION_API_KEY;
  const databaseId = process.env.NOTION_BRAND_PULSE_DATABASE_ID;
  if (!apiKey) {
    throw new ToolError("Missing NOTION_API_KEY environment variable.");
  }
  if (!databaseId) {
    throw new ToolError("Missing NOTION_BRAND_PULSE_DATABASE_ID environment variable.");
  }
  return { apiKey, databaseId };
}

async function appendToNotion(item) {
  const { apiKey, databaseId } = getNotionConfig();
  const notion = new NotionClient({ auth: apiKey });

  try {
    const response = await notion.pages.create({
      parent: { database_id: databaseId },
      properties: {
        Name: {
          title: [{ text: { content: item.place_name } }],
        },
        Type: {
          select: { name: item.type },
        },
        Content: {
          rich_text: [{ text: { content: item.content.slice(0, 1900) } }],
        },
        Status: {
          select: { name: item.status },
        },
      },
    });

    return {
      database_id: databaseId,
      page_id: response.id,
      url: response.url,
    };
  } catch (error) {
    throw new ToolError(`Notion write failed: ${error.message}`);
  }
}

function buildTrelloPayload(item) {
  return {
    action: "create_card",
    source: "winnovate_pulse_engine",
    type: item.type,
    place_name: item.place_name,
    title: item.type === "Friction" ? item.content : `Amplify praise: ${item.place_name}` ,
    description: item.content,
    status: item.status,
    labels: ["Brand Pulse", item.type],
  };
}

function buildTrelloUrl(payload) {
  const baseUrl = process.env.TRELLO_AUTOMATION_URL;
  if (!baseUrl) {
    throw new ToolError("Missing TRELLO_AUTOMATION_URL environment variable.");
  }
  const url = new URL(baseUrl);
  Object.entries(payload).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      url.searchParams.set(key, value.join(","));
    } else {
      url.searchParams.set(key, String(value));
    }
  });
  return url.toString();
}

async function main() {
  try {
    const { item: rawItem, route, mode } = parseCliInput(process.argv);
    const item = normalizeApprovedItem(rawItem);
    const result = {
      ok: true,
      place_name: item.place_name,
      type: item.type,
      status: item.status,
      notion: null,
      trello: null,
    };

    if (route === "notion" || route === "both") {
      result.notion = await appendToNotion(item);
    }

    if (route === "trello" || route === "both") {
      const payload = buildTrelloPayload(item);
      result.trello = mode === "url"
        ? { mode: "url", url: buildTrelloUrl(payload) }
        : { mode: "payload", payload };
    }

    process.stdout.write(JSON.stringify(result));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    process.stdout.write(JSON.stringify({ ok: false, error: message }));
    process.exitCode = 1;
  }
}

await main();
