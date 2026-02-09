package com.outfit.backend.client;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;

@Slf4j
@Component
@RequiredArgsConstructor
public class FastApiClient {

    private final WebClient fastApiWebClient;
    
    @Value("${fastapi.recommend-path:/recommend/image}")
    private String recommendPath;
    
    public Mono<JsonNode> recommend(
            Resource imageResource,
            int limit,
            boolean safe,
            String requestId,
            String textQuery,
            String metaJson
    ) {
        MultipartBodyBuilder body = new MultipartBodyBuilder();

        // ✅ FastAPI 계약: "image" (UploadFile), "requestId"(Form) 필수
        // ✅ filename 보정: Resource.getFilename()이 null일 수 있어서 기본값 지정
        String filename = (imageResource.getFilename() == null || imageResource.getFilename().isBlank())
                ? "image.jpg"
                : imageResource.getFilename();

        body.part("image", imageResource)
                .filename(filename)
                .contentType(MediaType.APPLICATION_OCTET_STREAM);

        body.part("requestId", requestId);
        body.part("limit", String.valueOf(limit));
        body.part("safe", String.valueOf(safe));

        if (textQuery != null && !textQuery.isBlank()) body.part("textQuery", textQuery);

        // ⚠️ 필드명 고정: 현재는 "meta"로 보냄 (FastAPI에서도 "meta"로 받게 고정해)
        if (metaJson != null && !metaJson.isBlank()) body.part("meta", metaJson);
        
        
        return fastApiWebClient.post()
                .uri(recommendPath)
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .accept(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromMultipartData(body.build()))
                .retrieve()
                // ✅ 4xx/5xx면 바디까지 읽어서 예외에 포함(디버깅 지옥 방지)
                .onStatus(
                        status -> status.is4xxClientError() || status.is5xxServerError(),
                        resp -> resp.bodyToMono(String.class)
                                .defaultIfEmpty("")
                                .map(bodyStr -> new RuntimeException(
                                        "FastAPI error: " + resp.statusCode() + " body=" + bodyStr
                                ))
                )
                .bodyToMono(JsonNode.class)
                // ✅ 모델/외부 API 때문에 timeout 필수
                .timeout(Duration.ofSeconds(30));
    }
}
