package com.tencent.trpc.core.transport;

import com.tencent.trpc.core.common.config.ProtocolConfig;
import com.tencent.trpc.core.transport.handler.ChannelHandlerAdapter;
import java.util.Set;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.*;

class PoolReplacementRaceTest {
    static class Transport extends AbstractClientTransport {
        final List<Channel> made = new CopyOnWriteArrayList<>();
        Transport(ProtocolConfig config) {
            super(config, new ChannelHandlerAdapter(), null);
            CyclicBarrier contenders = new CyclicBarrier(2);
            connLock = new ReentrantLock() {
                @Override public void lock() {
                    try { contenders.await(5, TimeUnit.SECONDS); }
                    catch (Exception e) { throw new AssertionError(e); }
                    super.lock();
                }
            };
        }
        protected void doOpen() {}
        protected void doClose() {}
        protected boolean useChannelPool() { return true; }
        protected CompletableFuture<Channel> make() {
            Channel channel = mock(Channel.class);
            AtomicBoolean active = new AtomicBoolean(true);
            when(channel.isConnected()).thenAnswer(i -> active.get());
            when(channel.close()).thenAnswer(i -> {
                active.set(false);
                return CompletableFuture.completedFuture(null);
            });
            made.add(channel);
            return CompletableFuture.completedFuture(channel);
        }
        public Set<Channel> getChannels() {
            Set<Channel> active = new HashSet<>();
            for (Channel channel : made) if (channel.isConnected()) active.add(channel);
            return active;
        }
    }
    @Test void closingTransportClosesAllConnectionsCreatedByConcurrentAcquisition() throws Exception {
        ProtocolConfig config = new ProtocolConfig();
        config.setIp("127.0.0.1");
        config.setPort(12345);
        config.setConnsPerAddr(1);
        config.setLazyinit(true);
        config.setKeepAlive(true);
        Transport transport = new Transport(config);
        ExecutorService workers = Executors.newFixedThreadPool(2);
        try {
            transport.open();
            Future<?> a = workers.submit(() -> transport.getChannel().toCompletableFuture().join());
            Future<?> b = workers.submit(() -> transport.getChannel().toCompletableFuture().join());
            a.get(10, TimeUnit.SECONDS);
            b.get(10, TimeUnit.SECONDS);
            transport.close();
            assertEquals(0, transport.getChannels().size(),
                    "Every connection created by the pool must be owned and closed by transport.close()");
        } finally {
            workers.shutdownNow();
            transport.close();
            for (Channel channel : transport.made) channel.close();
        }
    }
}
