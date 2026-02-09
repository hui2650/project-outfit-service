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
    
    // MAX_LIMIT는 향후 UX 실험 대비용 상한
    private static final int MAX_LIMIT = 12;

    /**
     * FastAPI raw(JsonNode) → Spring V1 고정 계약 DTO로 변환
     *
     * ✅ 흡수하는 변화/지뢰
     * - raw 배열 키: items / results 둘 다 허용
     * - 썸네일 키: thumbnailUrl / thumbnaiUrl(오타) 둘 다 허용
     * - 소스 키: source / Source(대문자) 둘 다 허용
     * - diagnostics/query: 최상위가 아니라 하위 노드에서 파싱
     *
     * @param raw FastAPI 응답 원본(JsonNode)
     * @param requestId Spring에서 만든 requestId (우선)
     * @param limit 프론트/서비스에서 받은 limit (1~12 clamp)
     * @param fallbackPrimaryQuery query.primary가 없을 때 대체 문자열(보통 사용자 입력 text)
     */
    public RecommendV1ResponseDTO toV1(JsonNode raw, String requestId, int limit, String fallbackTextQuery) {
        int finalLimit = clampLimit(limit);

        // ✅ items/results 호환: FastAPI 원본 배열 노드 확보
        JsonNode listNode = pickArrayNode(raw);

        // ✅ diagnostics 파싱(하위 노드)
        DiagnosticsDTO diagnostics = parseDiagnostics(raw, listNode);

        // ✅ query 파싱(하위 노드) + fallback
        QueryDTO query = parseQuery(raw, fallbackTextQuery);

        // ✅ normalized (없으면 unknown 고정)
        NormalizedDTO normalized = parseNormalized(raw);

        // ✅ items 변환
        List<ResultCardDTO> items = parseItems(listNode, finalLimit);

        // ✅ diagnostics.itemsCount 보정 (없거나 0이면 items.size로)
        diagnostics = fixItemsCount(diagnostics, items.size());

        // ✅ requestId: 파라미터 우선, 없으면 raw.requestId
        String finalRequestId = (requestId != null && !requestId.isBlank())
                ? requestId
                : text(raw, "requestId", null);

        return new RecommendV1ResponseDTO(
                finalRequestId,
                normalized,
                query,
                items,        // ✅ RecommendV1ResponseDTO가 items로 고정되어 있어야 함
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

    private DiagnosticsDTO parseDiagnostics(JsonNode raw, JsonNode listNode) {
        // FastAPI 응답 예시:
        // diagnostics: { mode, rawCount, itemsCount }
        JsonNode d = (raw == null) ? null : raw.get("diagnostics");

        String mode = text(d, "mode", null);
        int rawCount = intVal(d, "rawCount", 0);
        int itemsCount = intVal(d, "itemsCount",
                (listNode != null && listNode.isArray()) ? listNode.size() : 0
        );

        return new DiagnosticsDTO(mode, rawCount, itemsCount);
    }

    private QueryDTO parseQuery(JsonNode raw, String fallbackPrimaryQuery) {
        // FastAPI 응답 예시:
        // query: { primary, fallbacks: [] }
        JsonNode q = (raw == null) ? null : raw.get("query");

        String primary = text(q, "primary", null);
        if (primary == null || primary.isBlank()) {
            primary = (fallbackPrimaryQuery != null) ? fallbackPrimaryQuery : "";
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
        // FastAPI 응답 예시:
        // normalized: { category, color, style }
        JsonNode n = (raw == null) ? null : raw.get("normalized");
        if (n == null || n.isNull()) {
            return new NormalizedDTO("unknown", "unknown", "unknown");
        }

        return new NormalizedDTO(
                text(n, "category", "unknown"),
                text(n, "color", "unknown"),
                text(n, "style", "unknown")
        );
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

            // ✅ 썸네일 키 호환: thumbnailUrl / thumbnaiUrl
            String thumbnailUrl = text(it, "thumbnailUrl", null);
            if (thumbnailUrl == null || thumbnailUrl.isBlank()) {
                thumbnailUrl = text(it, "thumbnaiUrl", ""); // 오타 흡수
            }

            String title = text(it, "title", "No Title");

            // ✅ source 키 호환: source / Source
            String source = text(it, "source", null);
            if (source == null || source.isBlank()) {
                source = text(it, "Source", "Openverse");
            }

            boolean strict = boolVal(it, "strict", false);
            double score = doubleVal(it, "score", 0.0);

            items.add(new ResultCardDTO(rank++, imageUrl, thumbnailUrl, title, source, strict, score));
        }
        return items;
    }

    private DiagnosticsDTO fixItemsCount(DiagnosticsDTO d, int size) {
        if (d == null) return new DiagnosticsDTO(null, 0, size);
        int itemsCount = (d.itemsCount() > 0) ? d.itemsCount() : size;
        return new DiagnosticsDTO(d.mode(), d.rawCount(), itemsCount);
    }

    // -------------------------
    // safe getters (JsonNode)
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
