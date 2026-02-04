package com.outfit.backend.dto;

import java.util.List;

public record RecommendResponseDTO(
	String requestId,
    List<RecommendItemDTO> items
	) {

}
