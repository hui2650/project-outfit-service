package com.outfit.backend.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class RecommendationDetail {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "master_id")
    private RecommendationMaster master;

    private int rankNum;
    private String imageUrl;
    private String title;
    private String source;

    @Builder
    public RecommendationDetail(RecommendationMaster master, int rankNum, String imageUrl, String title, String source) {
        this.master = master;
        this.rankNum = rankNum;
        this.imageUrl = imageUrl;
        this.title = title;
        this.source = source;
    }
}