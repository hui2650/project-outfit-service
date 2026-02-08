package com.outfit.backend.service;

import java.io.IOException;
import java.util.List;
import java.util.UUID;
import java.util.Optional;

import org.springframework.http.MediaType;
import org.springframework.http.HttpHeaders;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import com.outfit.backend.dto.RecommendResponseDTO;
import com.outfit.backend.dto.RecommendItemDTO;
import com.outfit.backend.entity.RecommendationDetail;
import com.outfit.backend.entity.RecommendationMaster;
import com.outfit.backend.persistence.RecommendationRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class RecommendService {

    private final RecommendationRepository recRepository; // JpaRepository
    private final RestTemplate restTemplate = new RestTemplate(); // 객체를 하나 생성, postForObject() 같은 메서드로 HTTP를 쓴다
    										// RestTemplate: 스프링에서 '다른 서버에 HTTP 보내는 클라이언트'
    										// 지금 구조에서 스프링이 파이썬 서버를 호출해야 하니까 RestTemplate이 필요
    
    // 1. requestId 만들기
    // 2. 파이썬 서버에 multipart로 전달하고 응답 받기
    // 3. 응답을 DB에 저장하고 프론트에 반환

    public RecommendResponseDTO getRecommendations(MultipartFile image, int limit, String textQuery) {
    	
        // requestId 생성 -> 충돌 확률이 거의 없는 랜덤 식별자 생성 (중복X)
    	// “이 요청이 만든 8개 결과가 무엇인지” 연결해주는 키
    	String requestId = "req_" + UUID.randomUUID().toString().substring(0, 8); // 앞글자 8개만 자름
        
        
        // 1. 파이썬 서버로 보낼 요청 구성 (Multipart)
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>(); // MultiValueMap의 구현체(실제 객체
        // 키 하나에 값이 여러 개 붙을 수 있는 Map
        // tags=outfit&tags=street  이런 구조를 표현하려고 MultiValueMap을 씀
        

        ByteArrayResource imageResource;
        try {
            String filename = image.getOriginalFilename();
            if (filename == null || filename.isBlank()) filename = "upload.jpg";

            String finalFilename = filename; // ✅ 익명클래스에서 쓰려면 final/effectively final 필요
            imageResource = new ByteArrayResource(image.getBytes()) {
                @Override
                public String getFilename() {
                    return finalFilename;
                }
            };
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read upload file bytes", e);
        }

       
        
        body.add("image", imageResource);
        // HTTP로 파일을 보내려기 위해 “스프링이 이해하는 리소스 타입”으로 바꿈
        // MultipartFile(업로드 받은 파일) → Resource(전송 가능한 형태)
        body.add("limit", limit);
        body.add("requestId", requestId);
        
        if (textQuery != null && !textQuery.isBlank()) {
            body.add("textQuery", textQuery);
        }
        
        
        // multipart 요청 만들기: headers + body + HttpEntity
        // “내가 지금 multipart/form-data로 보낼 거야” 라고 선언
        
        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        // 2. 파이썬 서버 호출
        String pythonUrl = "http://localhost:8000/recommend/image"; // 실제 파이썬 주소
        RecommendResponseDTO pythonResponse = 
        		restTemplate.postForObject(pythonUrl, requestEntity, RecommendResponseDTO.class);
        // pythonUrl로 POST 요청을 보낸다
        // 요청 본문은 requestEntity (multipart)
        // 응답이 오면, 그 JSON을 RecommendResponseDTO.class 형태로 역직렬화해서 반환
        
//        즉:
//        	파이썬이 JSON으로
//        	requestId
//        	items[]
//        	를 보내면,
//
//        	Spring이 자동으로
//        	RecommendResponseDTO
//        	List<RecommendItemDTO>
//        	로 변환해준다.
   

        // pythonResponse가 null일때 던지기
    	if (pythonResponse == null) {
    	    throw new IllegalStateException("Python response is null");
    	}
    	
    	// // requestId 일관성 강제(파이썬이 echo 안 하면)
        // pythonResponse = new RecommendResponseDTO(requestId, pythonResponse.items());

        List<RecommendItemDTO> safeItems =
        Optional.ofNullable(pythonResponse.items()).orElseGet(List::of);

        pythonResponse = new RecommendResponseDTO(requestId, safeItems);

        // 비어있으면 저장 스킵(선택)
        // 저장 정책: "요청 로그는 남기되 detail은 비움" or "아예 저장 안 함" 중 택1
        if (!safeItems.isEmpty()) {
            saveToDatabase(pythonResponse);
        }
        return pythonResponse;

    }

    private void saveToDatabase(RecommendResponseDTO response) {
        List<RecommendItemDTO> items =
                Optional.ofNullable(response.items()).orElseGet(List::of);

        RecommendationMaster master = new RecommendationMaster(response.requestId());
       // RecommendationMaster를 만든다 = requestId가 저장됨, createdAt 생성됨
        
        // DTO의 items()를 stream으로 돌면서
        //각각을 RecommendationDetail 엔티티로 변환
        // master(master)로 연결
        List<RecommendationDetail> details = items.stream()
            .map(item -> RecommendationDetail.builder()
                .master(master)
                .rankNum(item.rank())
                .imageUrl(item.imageUrl())
                .title(item.title())
                .source(item.source())
                .build())
            .toList();
        
        // master.addDetail(detail)로 master.details 리스트에 넣음
        // “한 요청의 8개 결과”라는 관계가 리스트로 구성됨
        details.forEach(master::addDetail);
        
        recRepository.save(master);
        // master 저장
        // cascade 설정이 있다면 detail도 함께 저장
    }
}
