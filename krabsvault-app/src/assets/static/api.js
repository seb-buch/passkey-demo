/**
 * @param {string} url
 * @param {Object} [body]
 * @returns {Promise<Response>}
 */
async function apiPost(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    ...(body && {
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    }),
  });
  if (!resp.ok) {
    const err = await resp.json();
    throw new Error(err.error || resp.statusText);
  }
  return resp;
}
