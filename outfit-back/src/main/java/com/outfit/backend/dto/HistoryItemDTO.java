package com.outfit.backend.dto;

import java.time.LocalDateTime;

public record HistoryItemDTO(
	String requestId, LocalDateTime createdAt
	)

{

}
