package com.outfit.backend.persistence;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.outfit.backend.entity.RecommendationMaster;

import java.util.List;
import java.util.Optional;

@Repository
public interface RecommendationRepository extends JpaRepository<RecommendationMaster, Long> {
    // requestId로 특정 추천 이력을 찾을 때 사용
    Optional<RecommendationMaster> findByRequestId(String requestId);
    
    // 히스토리 목록 정렬할때
    List<RecommendationMaster> findAllByOrderByCreatedAtDesc();
}
