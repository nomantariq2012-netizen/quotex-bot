export default {
  async fetch(request, env, ctx) {
    // Aapke Bot ka Token aur Chat ID yahan set hain
    const TELEGRAM_BOT_TOKEN = "7547146524:AAGsB9QJ841zK0_example_token"; 
    const CHAT_ID = "6123456789"; 
    
    const message = "🤖 Quotex Signal Bot is live and running on Cloudflare Workers!";

    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
    
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: CHAT_ID, text: message })
      });
      
      const result = await response.json();
      return new Response("Bot message sent successfully! Response: " + JSON.stringify(result));
    } catch (error) {
      return new Response("Error sending message: " + error.message, { status: 500 });
    }
  },
};
