package com.outfit.backend.dto;

import java.util.List;

public record RecommendV1ResponseDTO( 
	String requestId,
	NormalizedDTO normalized,
	QueryDTO query,
	List<ResultCardDTO> items,
	DiagnosticsDTO diagnostics
) {}
