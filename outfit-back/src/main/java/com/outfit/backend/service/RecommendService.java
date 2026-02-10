package com.outfit.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.outfit.backend.adapter.RecommendResponseAdapter;
import com.outfit.backend.client.FastApiClient;
import com.outfit.backend.dto.RecommendV1ResponseDTO;
import com.outfit.backend.dto.ResultCardDTO;
import com.outfit.backend.entity.RecommendationDetail;
import com.outfit.backend.entity.RecommendationMaster;
import com.outfit.backend.persistence.RecommendationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class RecommendService {

    private final FastApiClient fastApiClient;
    private final RecommendResponseAdapter adapter;
    private final RecommendationRepository recRepository;

    public RecommendV1ResponseDTO getRecommendations(
            MultipartFile image,
            String textQuery,
            int limit,
            boolean safe,
            String category,
            String gender
    ) {
        String requestId = "req_" + UUID.randomUUID().toString().substring(0, 8);
        int finalLimit = clamp(limit, 1, 12, 8);

        String metaJson = null;

        JsonNode raw = fastApiClient
                .recommend(
                        image.getResource(),
                        finalLimit,
                        safe,
                        requestId,
                        category,
                        gender,
                        textQuery,
                        metaJson
                )
                .block();

        // fallbackPrimaryQuery는 textQuery
        RecommendV1ResponseDTO v1 = adapter.toV1(raw, requestId, finalLimit, textQuery);

        List<ResultCardDTO> items = Optional.ofNullable(v1.items()).orElseGet(List::of);
        if (!items.isEmpty()) {
            saveToDatabase(v1.requestId(), items);
        }

        return v1;
    }

    private void saveToDatabase(String requestId, List<ResultCardDTO> items) {
        RecommendationMaster master = new RecommendationMaster(requestId);

        List<RecommendationDetail> details = items.stream()
                .map(item -> RecommendationDetail.builder()
                        .master(master)
                        .rankNum(item.rank())
                        .imageUrl(item.imageUrl())
                        .title(item.title())
                        .source(item.source())
                        .build())
                .toList();

        details.forEach(master::addDetail);
        recRepository.save(master);
    }

    private int clamp(int v, int min, int max, int def) {
        if (v <= 0) return def;
        return Math.min(Math.max(v, min), max);
    }
}
