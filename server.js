#!/usr/bin/env node

const express = require("express");
const axios = require("axios");
const cheerio = require("cheerio");

const app = express();
const PORT = 9701;

app.get("/search", async (req, res) => {
  try {
    const query = req.query.q;

    if (!query) {
      return res.status(400).json({ error: "Missing query" });
    }

    const response = await axios.get(
      "https://www.themoviedb.org/search?query=" +
      encodeURIComponent(query)
    );

    const $ = cheerio.load(response.data);
    const results = [];

    $(".comp\\:media-card").each((i, el) => {
      const mediaLink = $(el)
        .find('a[href*="/movie/"], a[href*="/tv/"], a[href*="/collection/"]')
        .first()
        .attr("href");

      let tmdb_id = null;
      let media_type = null;

      if (mediaLink) {
        const movieMatch = mediaLink.match(/\/movie\/(\d+)/);
        const tvMatch = mediaLink.match(/\/tv\/(\d+)/);
        const collectionMatch = mediaLink.match(/\/collection\/(\d+)/);

        if (movieMatch) {
          tmdb_id = Number(movieMatch[1]);
          media_type = "movie";
        } else if (tvMatch) {
          tmdb_id = Number(tvMatch[1]);
          media_type = "tv";
        } else if (collectionMatch) {
          tmdb_id = Number(collectionMatch[1]);
          media_type = "collection";
        }
      }

      const title = $(el).find("h2 span").text().trim();
      const description = $(el).find(".mt-4 p").text().trim();
      const release_date = $(el)
        .find(".release_date")
        .text()
        .replace(/\s+/g, " ")
        .trim();

      const posterSrc = $(el).find("img.poster").attr("src");

      let poster = null;

      if (posterSrc) {
        poster = posterSrc.startsWith("http")
          ? posterSrc.replace("/w94_and_h141_face/", "/w500/")
          : "https://media.themoviedb.org" +
            posterSrc.replace("/w94_and_h141_face/", "/w500/");
      }

      results.push({
        tmdb_id,
        media_type,
        title,
        description,
        release_date,
        poster,
        url: mediaLink
          ? `https://www.themoviedb.org${mediaLink}`
          : null
      });
    });

    res.json({ results });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log("TMDB API running on port " + PORT);
});
