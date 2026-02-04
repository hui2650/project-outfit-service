package com.outfit.backend.entity;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.PrePersist;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;


@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class RecommendationMaster {
	@Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String requestId;
    private LocalDateTime createdAt;

    @OneToMany(mappedBy = "master", cascade = CascadeType.ALL)
    private List<RecommendationDetail> details = new ArrayList<>();

    public RecommendationMaster(String requestId) {
        this.requestId = requestId;
        this.createdAt = LocalDateTime.now();
    }

    public void addDetail(RecommendationDetail detail) {
        this.details.add(detail);
    }
    
    @PrePersist
    public void prePersist() {
        this.createdAt = LocalDateTime.now();
    }
    
    

}
