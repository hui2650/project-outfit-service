package com.outfit.backend.dto;

import java.util.List;

public record QueryDTO (
		String primary,
		List<String> fallbacks
) {}