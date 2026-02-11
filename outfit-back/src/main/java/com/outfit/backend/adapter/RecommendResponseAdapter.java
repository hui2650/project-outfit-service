package com.outfit.backend.adapter;

import com.fasterxml.jackson.databind.JsonNode;
import com.outfit.backend.dto.*;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

@Component
public class RecommendResponseAdapter {

    private static final int DEFAULT_LIMIT = 8;
    private static final int MAX_LIMIT = 12;

    /**
     * FastAPI raw(JsonNode) → Spring V1 고정 계약 DTO로 변환
     *
     *  흡수하는 변화/지뢰
     * - 배열 키: items / results 둘 다 허용
     * - 썸네일 키: thumbUrl / thumbnailUrl / thumbnaiUrl(오타) 허용
     * - 점수 키: rankScore / score 허용
     * - source 키: source / Source(대문자) 허용
     * - query: FastAPI가 문자열(query)로 줄 수도 있고 객체(query:{primary,...})로 줄 수도 있음
     * - diagnostics는 없을 수 있음 → 합성
     */
    public RecommendV1ResponseDTO toV1(JsonNode raw, String requestId, int limit, String fallbackTextQuery) {
        int finalLimit = clampLimit(limit);

        JsonNode listNode = pickArrayNode(raw);

        // items 변환
        List<ResultCardDTO> items = parseItems(listNode, finalLimit);

        // query 파싱(문자열/객체 호환) + fallback
        QueryDTO query = parseQuery(raw, fallbackTextQuery);

        // normalized (없으면 unknown)
        NormalizedDTO normalized = parseNormalized(raw);

        // diagnostics (없으면 합성)
        DiagnosticsDTO diagnostics = parseDiagnostics(raw, listNode, items.size());

        // requestId: 파라미터 우선, 없으면 raw.requestId
        String finalRequestId = (requestId != null && !requestId.isBlank())
                ? requestId
                : text(raw, "requestId", null);

        return new RecommendV1ResponseDTO(
                finalRequestId,
                normalized,
                query,
                items,
                diagnostics
        );
    }

    // -------------------------
    // parsing helpers
    // -------------------------

    private int clampLimit(int limit) {
        int v = (limit <= 0) ? DEFAULT_LIMIT : limit;
        if (v < 1) v = 1;
        if (v > MAX_LIMIT) v = MAX_LIMIT;
        return v;
    }

    /** raw.items 우선, 없으면 raw.results */
    private JsonNode pickArrayNode(JsonNode raw) {
        if (raw == null) return null;
        JsonNode items = raw.get("items");
        if (items != null && items.isArray()) return items;
        JsonNode results = raw.get("results");
        if (results != null && results.isArray()) return results;
        return null;
    }

    private List<ResultCardDTO> parseItems(JsonNode listNode, int limit) {
        List<ResultCardDTO> items = new ArrayList<>();
        if (listNode == null || !listNode.isArray()) return items;

        int rank = 1;
        for (JsonNode it : listNode) {
            if (items.size() >= limit) break;
            if (it == null || it.isNull()) continue;

            String imageUrl = text(it, "imageUrl", "");
            if (imageUrl.isBlank()) continue;

            //  썸네일 키 호환: thumbUrl / thumbnailUrl / thumbnaiUrl(오타)
            String thumbUrl = text(it, "thumbUrl", null);
            if (thumbUrl == null || thumbUrl.isBlank()) thumbUrl = text(it, "thumbnailUrl", null);
            if (thumbUrl == null || thumbUrl.isBlank()) thumbUrl = text(it, "thumbnaiUrl", "");

            String title = text(it, "title", "No Title");

            //  source 키 호환: source / Source
            String source = text(it, "source", null);
            if (source == null || source.isBlank()) source = text(it, "Source", "unknown");

            //  strict/score 호환
            boolean strict = boolVal(it, "strict", false);
            double score = doubleVal(it, "rankScore", Double.NaN);
            if (Double.isNaN(score)) score = doubleVal(it, "score", 0.0);

            items.add(new ResultCardDTO(rank++, imageUrl, thumbUrl, title, source, strict, score));
        }
        return items;
    }

    private QueryDTO parseQuery(JsonNode raw, String fallbackTextQuery) {
        if (raw == null) return new QueryDTO(fallbackTextQuery, Collections.emptyList());

        JsonNode q = raw.get("query");

        // FastAPI가 query를 문자열로 준 경우: "query": "...."
        if (q != null && q.isTextual()) {
            String primary = q.asText("");
            if (primary.isBlank()) primary = (fallbackTextQuery != null ? fallbackTextQuery : "");
            return new QueryDTO(primary, Collections.emptyList());
        }

        // 객체 형태: query: { primary, fallbacks: [] }
        String primary = text(q, "primary", null);
        if (primary == null || primary.isBlank()) {
            primary = (fallbackTextQuery != null) ? fallbackTextQuery : "";
        }

        List<String> fallbacks = new ArrayList<>();
        JsonNode fb = (q == null) ? null : q.get("fallbacks");
        if (fb != null && fb.isArray()) {
            for (JsonNode f : fb) {
                if (f != null && !f.isNull()) {
                    String s = f.asText();
                    if (s != null && !s.isBlank()) fallbacks.add(s);
                }
            }
        }

        return new QueryDTO(primary, fallbacks.isEmpty() ? Collections.emptyList() : fallbacks);
    }

    private NormalizedDTO parseNormalized(JsonNode raw) {
        JsonNode n = (raw == null) ? null : raw.get("normalized");
        if (n == null || n.isNull() || n.isMissingNode()) {
            return new NormalizedDTO("unknown", "unknown", "unknown");
        }
        return new NormalizedDTO(
                text(n, "category", "unknown"),
                text(n, "color", "unknown"),
                text(n, "style", "unknown")
        );
    }

    private DiagnosticsDTO parseDiagnostics(JsonNode raw, JsonNode listNode, int parsedSize) {
        // FastAPI 응답이 diagnostics를 안 줄 수도 있으니까 합성 가능
        JsonNode d = (raw == null) ? null : raw.get("diagnostics");

        String mode = text(d, "mode", null);

        // rawCount가 없으면 rawCandidateCount로라도 받기
        int rawCount = intVal(d, "rawCount", 0);
        if (rawCount == 0 && raw != null) rawCount = intVal(raw, "rawCandidateCount", 0);

        // itemsCount 없으면 listNode.size 또는 parsedSize
        int itemsCount = intVal(d, "itemsCount",
                (listNode != null && listNode.isArray()) ? listNode.size() : parsedSize
        );
        if (itemsCount == 0) itemsCount = parsedSize;

        return new DiagnosticsDTO(mode, rawCount, itemsCount);
    }

    // -------------------------
    // safe getters
    // -------------------------

    private String text(JsonNode n, String key, String def) {
        if (n == null) return def;
        JsonNode v = n.get(key);
        if (v == null || v.isNull()) return def;
        String s = v.asText();
        return (s == null || s.isBlank()) ? def : s;
    }

    private int intVal(JsonNode n, String key, int def) {
        if (n == null) return def;
        JsonNode v = n.get(key);
        if (v == null || v.isNull()) return def;
        return v.asInt(def);
    }

    private boolean boolVal(JsonNode n, String key, boolean def) {
        if (n == null) return def;
        JsonNode v = n.get(key);
        if (v == null || v.isNull()) return def;
        return v.asBoolean(def);
    }

    private double doubleVal(JsonNode n, String key, double def) {
        if (n == null) return def;
        JsonNode v = n.get(key);
        if (v == null || v.isNull()) return def;
        return v.asDouble(def);
    }
}
