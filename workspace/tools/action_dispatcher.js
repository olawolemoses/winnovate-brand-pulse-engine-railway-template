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

  if (jsonArgIndex === -1 || !args[jsonArgIndex + 1]) {
    throw new ToolError("Usage: node workspace/tools/action_dispatcher.js --item '<JSON>'");
  }

  try {
    return JSON.parse(args[jsonArgIndex + 1]);
  } catch (error) {
    throw new ToolError(`Invalid JSON passed to --item: ${error.message}`);
  }
}

function normalizeApprovedItem(rawItem) {
  if (!rawItem || typeof rawItem !== "object") {
    throw new ToolError("Approved item must be a JSON object.");
  }

  const pageId = rawItem.item_id || rawItem.page_id || rawItem.id || "";
  const placeName = rawItem.place_name || rawItem.placeName || "";
  const type = rawItem.type || rawItem.category || "";
  const content = rawItem.content || rawItem.punchy_quote || rawItem.trello_action_item || "";
  const reviewText = rawItem.review_text || rawItem.text || "";
  const author = rawItem.author || "";
  const rating = rawItem.rating;

  if (!pageId.trim()) {
    throw new ToolError("Approved item is missing item_id.");
  }
  if (!placeName.trim()) {
    throw new ToolError("Approved item is missing place_name.");
  }
  if (!["Praise", "Friction"].includes(type)) {
    throw new ToolError("Approved item type must be Praise or Friction.");
  }
  if (!content.trim()) {
    throw new ToolError("Approved item is missing content, punchy_quote, or trello_action_item.");
  }

  return {
    item_id: pageId.trim(),
    place_name: placeName.trim(),
    type,
    content: content.trim(),
    review_text: String(reviewText || "").trim(),
    author: String(author || "").trim(),
    rating: typeof rating === "number" ? rating : null,
  };
}

function getNotionClient() {
  const token = process.env.NOTION_TOKEN || process.env.NOTION_API_KEY;
  if (!token) {
    throw new ToolError("Missing NOTION_TOKEN environment variable.");
  }
  return new NotionClient({ auth: token });
}

function buildTrelloDescription(item) {
  const parts = [];
  if (item.review_text) {
    parts.push(`Review: ${item.review_text}`);
  }
  if (item.author) {
    parts.push(`Author: ${item.author}`);
  }
  if (item.rating !== null) {
    parts.push(`Rating: ${item.rating} star(s)`);
  }
  return parts.join("\n");
}

async function createTrelloTask(item) {
  const idList = process.env.TRELLO_LIST_ID;
  const key = process.env.TRELLO_KEY;
  const token = process.env.TRELLO_TOKEN;

  if (!idList || !key || !token) {
    throw new ToolError("Missing Trello environment variables. Expected TRELLO_LIST_ID, TRELLO_KEY, and TRELLO_TOKEN.");
  }

  try {
    const response = await fetch("https://api.trello.com/1/cards", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: item.content,
        desc: buildTrelloDescription(item),
        idList,
        key,
        token,
        pos: "top",
      }),
    });

    if (!response.ok) {
      const details = await response.text().catch(() => "");
      throw new ToolError(`Trello card creation failed: ${details || response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ToolError) {
      throw error;
    }
    throw new ToolError(`Trello card creation failed: ${error.message}`);
  }
}

async function updateNotionItem(item, updates) {
  const notion = getNotionClient();
  const properties = {
    Status: { select: { name: updates.status } },
  };

  // If there's a Trello link, append it to Original Review
  if (updates.ticketLink) {
    const reviewText = item.review_text || "";
    const trelloNote = `\n\n📋 Trello: ${updates.ticketLink}`;
    properties["Original Review"] = {
      rich_text: [{ text: { content: (reviewText + trelloNote).slice(0, 2000) } }],
    };
  }

  try {
    const response = await notion.pages.update({
      page_id: item.item_id,
      properties,
    });
    return {
      page_id: response.id,
      url: response.url,
      status: updates.status,
      ticket_link: updates.ticketLink || null,
    };
  } catch (error) {
    throw new ToolError(`Notion update failed: ${error.message}`);
  }
}

async function main() {
  try {
    const item = normalizeApprovedItem(parseCliInput(process.argv));
    const result = {
      ok: true,
      item_id: item.item_id,
      place_name: item.place_name,
      type: item.type,
      notion: null,
      trello: null,
    };

    if (item.type === "Friction") {
      const trelloCard = await createTrelloTask(item);
      result.trello = {
        id: trelloCard.id,
        url: trelloCard.url,
        name: trelloCard.name,
      };
      result.notion = await updateNotionItem(item, {
        status: "Sent to Trello",
        ticketLink: trelloCard.url,
      });
    } else {
      result.notion = await updateNotionItem(item, {
        status: "Live",
      });
    }

    process.stdout.write(JSON.stringify(result));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    process.stdout.write(JSON.stringify({ ok: false, error: message }));
    process.exitCode = 1;
  }
}

await main();
