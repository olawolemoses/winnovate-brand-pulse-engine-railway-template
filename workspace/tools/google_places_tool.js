#!/usr/bin/env node
import { Client } from "@googlemaps/google-maps-services-js";

const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60;

class ToolError extends Error {
  constructor(message) {
    super(message);
    this.name = "ToolError";
  }
}

function parseArgs(argv) {
  const args = argv.slice(2);
  if (args.length === 0) {
    throw new ToolError("Usage: node workspace/tools/google_places_tool.js <PLACE_ID> [--max-results N]");
  }

  const placeId = args[0];
  let maxResults = 5;

  for (let i = 1; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--max-results") {
      const value = Number.parseInt(args[i + 1] || "", 10);
      if (!Number.isInteger(value) || value < 0) {
        throw new ToolError("--max-results must be a non-negative integer.");
      }
      maxResults = value;
      i += 1;
    }
  }

  return { placeId, maxResults };
}

function getApiKey() {
  const apiKey = process.env.Maps_API_KEY;
  if (!apiKey) {
    throw new ToolError("Missing Maps_API_KEY environment variable.");
  }
  return apiKey;
}

async function fetchPlaceDetails(client, placeId, apiKey) {
  let response;
  try {
    response = await client.placeDetails({
      params: {
        place_id: placeId,
        fields: ["name", "reviews"],
        key: apiKey,
      },
      timeout: 10000,
    });
  } catch (error) {
    throw new ToolError(`Google Places API request failed: ${error.message}`);
  }

  const data = response.data;
  if (data.status !== "OK") {
    const details = data.error_message ? `${data.status}: ${data.error_message}` : data.status;
    throw new ToolError(`Google Places API returned an error for place_id ${placeId}: ${details}`);
  }

  if (!data.result) {
    throw new ToolError(`No place details found for place_id ${placeId}.`);
  }

  return data.result;
}

function buildReviewPayload(review) {
  return {
    author: review.author_name || "",
    rating: review.rating ?? null,
    text: (review.text || "").trim(),
    relative_time: review.relative_time_description || "",
    timestamp: review.time ?? null,
  };
}

function filterRecentReviews(reviews, nowTs, maxResults) {
  const cutoff = nowTs - SEVEN_DAYS_SECONDS;
  const recentReviews = reviews
    .filter((review) => Number.isInteger(review.time) && review.time > cutoff)
    .map(buildReviewPayload)
    .sort((a, b) => b.timestamp - a.timestamp);

  return maxResults > 0 ? recentReviews.slice(0, maxResults) : recentReviews;
}

async function main() {
  try {
    const { placeId, maxResults } = parseArgs(process.argv);
    const apiKey = getApiKey();
    const client = new Client({});
    const place = await fetchPlaceDetails(client, placeId, apiKey);
    const reviews = Array.isArray(place.reviews) ? place.reviews : [];
    const filteredReviews = filterRecentReviews(reviews, Math.floor(Date.now() / 1000), maxResults);

    if (filteredReviews.length === 0) {
      throw new ToolError(`No reviews from the last 7 days were found for place_id ${placeId}.`);
    }

    process.stdout.write(JSON.stringify({
      ok: true,
      place_id: placeId,
      place_name: place.name || "",
      review_count: filteredReviews.length,
      reviews: filteredReviews,
    }));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error.";
    const placeId = process.argv[2] || "";
    process.stdout.write(JSON.stringify({
      ok: false,
      place_id: placeId,
      error: message,
      reviews: [],
    }));
    process.exitCode = 1;
  }
}

await main();
