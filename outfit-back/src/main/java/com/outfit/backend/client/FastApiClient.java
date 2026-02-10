package com.outfit.backend.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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

    @Value("${fastapi.recommend-path:/api/v1/recommend/image}")
    private String recommendPath;

    private final ObjectMapper om = new ObjectMapper();

    public Mono<JsonNode> recommend(
            Resource imageResource,
            int limit,
            boolean safe,
            String requestId,
            String category,
            String gender,
            String textQuery,
            String metaJson
    ) {
        MultipartBodyBuilder body = new MultipartBodyBuilder();

        // filename 보정
        String filename = (imageResource.getFilename() == null || imageResource.getFilename().isBlank())
                ? "image.jpg"
                : imageResource.getFilename();

        body.part("image", imageResource)
                .filename(filename)
                .contentType(MediaType.APPLICATION_OCTET_STREAM);

        // FastAPI는 Form으로 받으니까 전부 문자열로 보내도 OK
        body.part("requestId", requestId);
        body.part("limit", String.valueOf(limit));
        body.part("safe", String.valueOf(safe));
        body.part("textQuery", textQuery != null ? textQuery : "");
        body.part("category", category != null ? category : "");
        body.part("gender", gender != null ? gender : "");

        if (metaJson != null && !metaJson.isBlank()) {
            body.part("meta", metaJson);
        }

        log.info("[FASTAPI] POST {} | requestId={} limit={} safe={} textQuery='{}' category='{}' gender='{}'",
                recommendPath, requestId, limit, safe,
                (textQuery == null ? "" : textQuery),
                (category == null ? "" : category),
                (gender == null ? "" : gender)
        );

        return fastApiWebClient.post()
                .uri(recommendPath)
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(body.build()))
                .exchangeToMono(resp ->
                        resp.bodyToMono(String.class)
                                .defaultIfEmpty("")
                                .flatMap(bodyStr -> {
                                    log.info("[FASTAPI] status={} body={}", resp.statusCode(), bodyStr);

                                    if (resp.statusCode().isError()) {
                                        return Mono.error(new RuntimeException(
                                                "FastAPI error: " + resp.statusCode() + " body=" + bodyStr
                                        ));
                                    }

                                    try {
                                        JsonNode node = om.readTree(bodyStr);
                                        return Mono.just(node);
                                    } catch (Exception e) {
                                        return Mono.error(new RuntimeException(
                                                "FastAPI response JSON parse failed. body=" + bodyStr, e
                                        ));
                                    }
                                })
                )
                .timeout(Duration.ofSeconds(180));
    }
}
