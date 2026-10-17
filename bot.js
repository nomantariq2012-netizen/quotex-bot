export default {
  async fetch(request, env, ctx) {
    const TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN";
    const CHAT_ID = "YOUR_CHAT_ID";
    const message = "Quotex Bot is running on Cloudflare Workers!";

    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
    
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: CHAT_ID, text: message })
    });

    return new Response("Bot executed successfully!");
  },
};
