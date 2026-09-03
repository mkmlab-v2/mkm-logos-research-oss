/** Minimal Worker: serve static OPEN_BETA assets for mutda.ai */
export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  },
};
