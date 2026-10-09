import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.tencent.trpc.spring.boot.starters.context.configuration.TRpcConfigurationProperties;
import com.tencent.trpc.spring.boot.starters.context.configuration.bind.TRpcConfigurationBindResult;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** No Spring context, network listeners or remote dependencies: configuration mapping only. */
public final class JacksonBindingProbe {
    private static void equal(Object expected, Object actual) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError("Expected " + expected + ", got " + actual);
        }
    }

    public static void main(String[] args) throws Exception {
        equal(args[0], new ObjectMapper().version().toString());
        var properties = new TRpcConfigurationProperties();
        properties.getGlobal().setNamespace("Development");
        properties.getGlobal().setEnvName("local-validation");
        properties.getGlobal().setFullSetName("group.area.unit");
        properties.getGlobal().setContainerName("local-container");
        properties.getGlobal().setExt(Map.of("customKey", "unchanged", "nested", Map.of("userKey", 17)));
        properties.getServer().setLocalIp("127.0.0.1");
        properties.getServer().setRequestTimeout(1234);
        properties.getServer().setEnableLinkTimeout(false);
        properties.getServer().setRunListeners(List.of("local-listener"));
        properties.getClient().setRequestTimeout(2345);
        properties.getClient().setCallerServiceName("local-caller");
        Map<String, Object> result = new TRpcConfigurationBindResult(properties).toMap();
        Map<?, ?> global = (Map<?, ?>) result.get("global");
        equal("local-validation", global.get("env_name"));
        equal("group.area.unit", global.get("full_set_name"));
        equal("local-container", global.get("container_name"));
        equal("Development", global.get("namespace"));
        equal(false, global.containsKey("envName"));
        equal(false, global.containsKey("enable_set"));
        equal(Map.of("customKey", "unchanged", "nested", Map.of("userKey", 17)), global.get("ext"));
        Map<?, ?> server = (Map<?, ?>) result.get("server");
        equal("127.0.0.1", server.get("local_ip"));
        equal(1234, server.get("request_timeout"));
        equal(false, server.get("enable_link_timeout"));
        equal(List.of("local-listener"), server.get("run_listeners"));
        Map<?, ?> client = (Map<?, ?>) result.get("client");
        equal(2345, client.get("request_timeout"));
        equal("local-caller", client.get("caller_service_name"));
        var mapper = new ObjectMapper().enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
        System.out.println("CONFIG_JSON " + mapper.writeValueAsString(result));
        System.out.println("BINDER_SOURCE " + TRpcConfigurationBindResult.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("JACKSON_SOURCE " + ObjectMapper.class.getProtectionDomain().getCodeSource().getLocation());
        System.out.println("BINDING_PROBE_SUCCESS");
    }
}
