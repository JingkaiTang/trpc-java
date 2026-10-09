package com.tencent.trpc.spring.boot.starters;

import com.tencent.trpc.spring.boot.starters.context.configuration.TRpcConfigurationProperties;
import com.tencent.trpc.spring.boot.starters.context.configuration.bind.TRpcConfigurationBindResult;
import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class ConfigurationBindingTest {
    @Test void jacksonPreservesTrpcSnakeCaseConfiguration() {
        TRpcConfigurationProperties properties = new TRpcConfigurationProperties();
        properties.getGlobal().setEnvName("local-validation");
        Map<String, Object> result = new TRpcConfigurationBindResult(properties).toMap();
        Map<?, ?> global = (Map<?, ?>) result.get("global");
        assertEquals("local-validation", global.get("env_name"));
        assertFalse(global.containsKey("envName"));
    }
}
