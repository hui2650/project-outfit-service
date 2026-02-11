package com.outfit.backend.controller;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class ChatController {

    private final WebClient fastApiWebClient;

    //  Config에서 만든 fastApiWebClient 빈을 그대로 주입받음
    public ChatController(
            @Qualifier("fastApiWebClient") WebClient fastApiWebClient
    ) {
        this.fastApiWebClient = fastApiWebClient;
    }

    @PostMapping("/chat")
    public Mono<Map<String, Object>> chat(@RequestBody Map<String, Object> body) {
    return fastApiWebClient.post()
            .uri("/api/v1/chat")   // FastAPI 엔드포인트 정확히
            .bodyValue(body)
            .retrieve()
            .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {});
    }


    @GetMapping("/chat")
    public Map<String, Object> ping() {

        return Map.of("ok", true, "message", "ChatController is up");
    }

}
