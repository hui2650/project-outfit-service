package com.outfit.backend.dto;

import java.util.List;

public record HistoryListResponseDTO(
	List<HistoryItemDTO> items
		) {

}
