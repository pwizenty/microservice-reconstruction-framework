package com.example.gateway;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * A client of a service of the system whose address is defined nowhere. The url
 * element of a Feign client is an address by definition, so the call is
 * reported with an unresolved scheme rather than dropped - and the transport of
 * the gateway becomes unresolved rather than tls, because one call of unknown
 * transport is enough to make the whole of it unknown.
 */
@FeignClient(name = "reporting", url = "${reporting.baseURL}")
public interface ReportingClient {
    @GetMapping(value = "/reports")
    String getReports();
}
