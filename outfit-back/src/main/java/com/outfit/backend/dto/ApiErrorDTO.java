package com.outfit.backend.dto;

public record ApiErrorDTO(
	 String code,
	 String message
) {
	public static ApiErrorDTO of(String code, String message) {
		return new ApiErrorDTO(code, message);
	}
}
