package com.outfit.backend.controller;

import com.outfit.backend.dto.RecommendV1ResponseDTO;
import com.outfit.backend.service.RecommendService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/recommend")
public class RecommendController {

    private final RecommendService recommendService;

    @PostMapping(value = "/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public RecommendV1ResponseDTO recommendImage(
            @RequestPart("image") MultipartFile image,
            @RequestParam(value = "textQuery", required = false) String textQuery,
            @RequestParam(value = "limit", defaultValue = "8") int limit,
            @RequestParam(value = "safe", defaultValue = "true") boolean safe,
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "gender", required = false) String gender


            
    ) {
        return recommendService.getRecommendations(image, textQuery, limit, safe, category, gender);
    }
}
