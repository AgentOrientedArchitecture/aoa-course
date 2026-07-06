import { eveChannel } from "eve/channels/eve";
import { localDev, none } from "eve/channels/auth";

// This EVE runtime is never exposed to the host: its port is bound to loopback
// inside the container and only the co-located aoa-eve adapter calls it. localDev
// covers those loopback calls; none() keeps it open for the adapter without a
// credential dance. The governed, authenticated surface students interact with is
// the AOA A2A endpoint the adapter publishes on :8888, not this channel.
export default eveChannel({
  auth: [localDev(), none()],
});
