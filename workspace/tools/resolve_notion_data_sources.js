#!/usr/bin/env node
import { Client } from "@notionhq/client";

class ToolError extends Error {
  constructor(message) {
    super(message);
    this.name = "ToolError";
  }
}

function getEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new ToolError(`Missing ${name} environment variable.`);
  }
  return value;
}

async function resolveDatabase(client, label, databaseId) {
  const result = await client.databases.retrieve({ database_id: databaseId });
  const dataSources = Array.isArray(result.data_sources) ? result.data_sources : [];
  return {
    label,
    database_id: result.id || databaseId,
    data_sources: dataSources.map((source) => ({
      id: source.id,
      name: source.name || "",
    })),
  };
}

async function main() {
  try {
    const token = getEnv("NOTION_TOKEN");
    const brandDbId = getEnv("NOTION_BRAND_DB_ID");
    const pulseDbId = getEnv("NOTION_PULSE_DB_ID");
    const client = new Client({ auth: token });

    const brand = await resolveDatabase(client, "brand", brandDbId);
    const pulse = await resolveDatabase(client, "pulse", pulseDbId);

    process.stdout.write(JSON.stringify({ ok: true, brand, pulse }, null, 2));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    process.stdout.write(JSON.stringify({ ok: false, error: message }, null, 2));
    process.exitCode = 1;
  }
}

await main();
