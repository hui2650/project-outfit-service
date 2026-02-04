package com.outfit.backend.controller;

import org.springframework.http.MediaType;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.outfit.backend.dto.RecommendResponseDTO;
import com.outfit.backend.service.RecommendService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/v1/recommend")
@RequiredArgsConstructor
public class RecommendController {

    private final RecommendService recommendService;

    // 프론트가 POST /api/v1/recommend/image로 요청을 보냄
    // 요청은 “파일 업로드”이므로 multipart/form-data 형식
    
    // consumes는 “이 엔드포인트가 어떤 Content-Type 요청만 받는지”를 제한하는 옵션
    // MediaType.MULTIPART_FORM_DATA_VALUE는 문자열로는 "multipart/form-data"
    // 즉, 이 메서드는 multipart 업로드 요청만 허용
    @PostMapping(value = "/image", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<RecommendResponseDTO> recommendImage(
    		
    		//Spring이 multipart 요청에서 “파일 파트”를 잡아주는 타입.

    		//파일의 이름, 사이즈, content-type, 바이트 스트림을 다룰 수 있다.
    		// 서비스에서 image.getResource() 사용중
            @RequestParam("image") MultipartFile image, // 파일 파트 → MultipartFile image
            @RequestParam(value = "limit", defaultValue = "8") int limit, // 숫자 파트 → int limit
            @RequestParam(value="textQuery", required=false) String textQuery
            ) 
    {     
    	// 서비스가 만든 응답 DTO를 그대로 JSON으로 반환
        RecommendResponseDTO response = recommendService.getRecommendations(image, limit, textQuery);
        return ResponseEntity.ok(response);
    }
}












