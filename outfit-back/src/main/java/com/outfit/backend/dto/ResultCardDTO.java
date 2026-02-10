package com.outfit.backend.dto;

public record ResultCardDTO (
	int rank,
	String imageUrl,
	String thumbnailUrl,
	String title,
	String source,
	boolean strict,
	double score
) {}
