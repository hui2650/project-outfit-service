package com.outfit.backend.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

@Configuration
public class WebClientConfig {
	
	@Bean
	public WebClient fastApiWebClient(
			@Value("${fastapi.base-url}") String baseUrl,
			@Value("${fastapi.connect-timeout-ms:5000}") int connectTimeoutMs,
			@Value("${fastapi.read-timeout-ms:60000}") int readTimeoutMs
		) {
		HttpClient httpClient = HttpClient.create()
				.option(ChannelOption.CONNECT_TIMEOUT_MILLIS, connectTimeoutMs)
				.responseTimeout(Duration.ofMillis(readTimeoutMs))
				.doOnConnected(conn -> conn
						.addHandlerLast(new ReadTimeoutHandler(readTimeoutMs, TimeUnit.MILLISECONDS))
						.addHandlerLast(new WriteTimeoutHandler(readTimeoutMs, TimeUnit.MILLISECONDS)));
	
		// mulitipart , JsonNode 응답이 크면 buffer 제한 이슈가 생길 수 있어 상향(필요 시)
		ExchangeStrategies strategies = ExchangeStrategies.builder()
				.codecs(c -> c.defaultCodecs().maxInMemorySize(4 * 1024 * 1024))
				.build();
		
		return WebClient.builder()
				.baseUrl(baseUrl)
				.clientConnector(new ReactorClientHttpConnector(httpClient))
				.exchangeStrategies(strategies)
				.build();
	}
}
