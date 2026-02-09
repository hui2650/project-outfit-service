package com.outfit.backend.adapter;

import com.fasterxml.jackson.databind.JsonNode;
import com.outfit.backend.dto.*;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class RecommendAdapter {

    public RecommendV1ResponseDTO toV1(JsonNode raw) {
        // requestId
        String requestId = textOrNull(raw, "requestId");

        // normalized / query / diagnostics
        NormalizedDTO normalized = parseNormalized(raw.path("normalized"));
        QueryDTO query = parseQuery(raw.path("query"));
        DiagnosticsDTO diagnostics = parseDiagnostics(raw.path("diagnostics"));

        // ✅ FastAPI 호환: items 또는 results
        JsonNode listNode = raw.hasNonNull("items") ? raw.get("items") : raw.get("results");

        List<ResultCardDTO> items = new ArrayList<>();
        if (listNode != null && listNode.isArray()) {
            for (JsonNode it : listNode) {
                int rank = it.path("rank").asInt(0);
                String imageUrl = textOrNull(it, "imageUrl");

                // ✅ 썸네일 오타/호환 처리
                String thumbnailUrl = it.hasNonNull("thumbnailUrl")
                        ? it.get("thumbnailUrl").asText()
                        : textOrNull(it, "thumbnaiUrl");

                String title = textOrNull(it, "title");

                // ✅ source 대소문자 호환
                String source = it.hasNonNull("source")
                        ? it.get("source").asText()
                        : textOrNull(it, "Source");

                boolean strict = it.path("strict").asBoolean(false);
                double score = it.path("score").asDouble(0.0);

                items.add(new ResultCardDTO(
                        rank,
                        imageUrl,
                        thumbnailUrl,
                        title,
                        source,
                        strict,
                        score
                ));
            }
        }

        // ✅ diagnostics.itemsCount 보정
        diagnostics = fixItemsCount(diagnostics, items.size());

        return new RecommendV1ResponseDTO(
                requestId,
                normalized,
                query,
                items,
                diagnostics
        );
    }

    // ---------- sub parsers ----------

    private NormalizedDTO parseNormalized(JsonNode n) {
        if (n == null || n.isMissingNode() || n.isNull()) {
            return new NormalizedDTO("unknown", "unknown", "unknown");
        }
        return new NormalizedDTO(
                n.path("category").asText("unknown"),
                n.path("color").asText("unknown"),
                n.path("style").asText("unknown")
        );
    }

    private QueryDTO parseQuery(JsonNode q) {
        if (q == null || q.isMissingNode() || q.isNull()) {
            return new QueryDTO(null, Collections.emptyList());
        }

        String primary = q.path("primary").asText(null);

        List<String> fallbacks = new ArrayList<>();
        JsonNode fb = q.get("fallbacks");
        if (fb != null && fb.isArray()) {
            for (JsonNode f : fb) {
                if (!f.isNull()) fallbacks.add(f.asText());
            }
        }

        return new QueryDTO(primary, fallbacks);
    }

    private DiagnosticsDTO parseDiagnostics(JsonNode d) {
        if (d == null || d.isMissingNode() || d.isNull()) {
            return null;
        }
        String mode = d.path("mode").asText(null);
        int rawCount = d.path("rawCount").asInt(0);
        int itemsCount = d.path("itemsCount").asInt(0);
        return new DiagnosticsDTO(mode, rawCount, itemsCount);
    }

    private DiagnosticsDTO fixItemsCount(DiagnosticsDTO d, int size) {
        if (d == null) {
            return new DiagnosticsDTO(null, 0, size);
        }
        int itemsCount = d.itemsCount() > 0 ? d.itemsCount() : size;
        return new DiagnosticsDTO(d.mode(), d.rawCount(), itemsCount);
    }

    private String textOrNull(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return (v == null || v.isNull()) ? null : v.asText();
    }
}
