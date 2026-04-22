const HOST_NAME = "com.gptokens.bridge";
const DEFAULT_PLAN = "plus";

async function getQuotaConfig() {
  const url = chrome.runtime.getURL("quota.json");
  const response = await fetch(url);
  return await response.json();
}

async function getActivePlan() {
  const result = await chrome.storage.local.get(["activePlan"]);
  return result.activePlan || DEFAULT_PLAN;
}

async function setActivePlan(plan) {
  await chrome.storage.local.set({ activePlan: plan });
}

function bucketForPlan(config, plan) {
  const mapping = {
    free: config.free || [],
    plus: config.plus || [],
    team: config.team || [],
    pro: config.pro || []
  };
  return mapping[plan] || mapping.plus || [];
}

async function allKnownModels() {
  const config = await getQuotaConfig();
  const seen = new Map();
  for (const bucket of [config.models || [], config.free || [], config.plus || [], config.team || [], config.pro || []]) {
    for (const model of bucket) {
      if (model && model.id && !seen.has(model.id)) {
        seen.set(model.id, model);
      }
    }
  }
  return Array.from(seen.values());
}

async function mapApiModelToId(apiModelSlug) {
  if (!apiModelSlug) {
    return null;
  }

  const models = await allKnownModels();
  const exact = models.find((model) => model.id === apiModelSlug);
  if (exact) {
    return exact.id;
  }

  const sorted = [...models].sort((a, b) => b.id.length - a.id.length);
  for (const model of sorted) {
    const alt = model.id.includes(".") ? model.id.replace(".", "-") : null;
    if (apiModelSlug.includes(model.id)) {
      return model.id;
    }
    if (alt && apiModelSlug.includes(alt)) {
      return model.id;
    }
  }

  if (apiModelSlug === "auto") {
    return "auto";
  }
  return null;
}

async function appendTimestamp(modelId) {
  const key = `timestamps_${modelId}`;
  const result = await chrome.storage.local.get([key]);
  const timestamps = result[key] || [];
  timestamps.push(Date.now());
  await chrome.storage.local.set({ [key]: timestamps });
}

async function cleanupOldTimestamps() {
  const models = await allKnownModels();
  if (!models.length) {
    return;
  }
  const longest = Math.max(...models.map((model) => model.hours || 24));
  const threshold = Date.now() - (longest * 60 * 60 * 1000 * 1.5);
  const keys = models.map((model) => `timestamps_${model.id}`);
  const result = await chrome.storage.local.get(keys);
  const changes = {};

  for (const key of keys) {
    const timestamps = result[key] || [];
    changes[key] = timestamps.filter((timestamp) => timestamp >= threshold);
  }
  await chrome.storage.local.set(changes);
}

async function computeUsageState() {
  const plan = await getActivePlan();
  const config = await getQuotaConfig();
  const models = bucketForPlan(config, plan);
  const keys = models.map((model) => `timestamps_${model.id}`);
  const stored = await chrome.storage.local.get(keys);
  const now = Date.now();

  const usageModels = models.map((model) => {
    const timestamps = stored[`timestamps_${model.id}`] || [];
    const windowStart = now - (model.hours * 60 * 60 * 1000);
    const used = timestamps.filter((timestamp) => timestamp >= windowStart).length;
    return {
      id: model.id,
      used,
      quota: model.quota,
      hours: model.hours,
      max: typeof model.max === "number" ? model.max : null
    };
  });

  return {
    type: "write_state",
    source: "gptokens-companion",
    plan,
    models: usageModels
  };
}

async function sendUsageState() {
  try {
    const state = await computeUsageState();
    await chrome.runtime.sendNativeMessage(HOST_NAME, state);
  } catch (error) {
    console.warn("Unable to send usage state to native host:", error);
  }
}

chrome.webRequest.onBeforeRequest.addListener(
  async (details) => {
    if (details.method !== "POST" || !details.requestBody || !details.requestBody.raw) {
      return;
    }

    try {
      const bodyStr = new TextDecoder("utf-8").decode(details.requestBody.raw[0].bytes);
      const body = JSON.parse(bodyStr);
      const modelId = await mapApiModelToId(body.model);
      if (!modelId) {
        return;
      }
      await appendTimestamp(modelId);
      if (modelId === "gpt-5") {
        await appendTimestamp("auto");
      }
      await sendUsageState();
    } catch (error) {
      console.warn("Unable to parse request body:", error);
    }
  },
  {
    urls: [
      "*://chatgpt.com/backend-api/conversation",
      "*://chatgpt.com/backend-api/*/conversation"
    ]
  },
  ["requestBody"]
);

chrome.runtime.onInstalled.addListener(async () => {
  chrome.alarms.create("dailyCleanup", { periodInMinutes: 1440 });
  await sendUsageState();
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "dailyCleanup") {
    await cleanupOldTimestamps();
    await sendUsageState();
  }
});

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  (async () => {
    if (request.action === "getUsageData") {
      const plan = await getActivePlan();
      const state = await computeUsageState();
      sendResponse({ plan, models: state.models });
      return;
    }
    if (request.action === "setActivePlan") {
      await setActivePlan(request.plan);
      await sendUsageState();
      sendResponse({ ok: true });
      return;
    }
    if (request.action === "syncNow") {
      await sendUsageState();
      sendResponse({ ok: true });
    }
  })();
  return true;
});
