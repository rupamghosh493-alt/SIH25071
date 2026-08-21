const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("chatMessages");
const typing = document.getElementById("typing");
const sendButton = document.getElementById("sendButton");


function addMessage(text, type) {

    const wrapper = document.createElement("div");

    wrapper.className =
        "message " +
        (type === "user"
            ? "user-message"
            : "ai-message");


    const avatar = document.createElement("div");

    avatar.className = "avatar";

    avatar.textContent =
        type === "user"
            ? "YOU"
            : "AI";


    const content = document.createElement("div");

    content.className = "message-content";


    const name = document.createElement("div");

    name.className = "message-name";

    name.textContent =
        type === "user"
            ? "You"
            : "MineSafety_AI";


    const bubble = document.createElement("div");

    bubble.className = "message-bubble";

    bubble.textContent = text;


    content.appendChild(name);
    content.appendChild(bubble);

    wrapper.appendChild(avatar);
    wrapper.appendChild(content);

    messages.appendChild(wrapper);

    messages.scrollTop = messages.scrollHeight;
}


form.addEventListener("submit", async function(event) {

    event.preventDefault();

    const message = input.value.trim();

    if (!message) {
        return;
    }


    addMessage(message, "user");

    input.value = "";

    input.style.height = "auto";


    typing.style.display = "flex";

    sendButton.disabled = true;


    try {

        const response = await fetch("/api/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })

        });


        const data = await response.json();


        if (!response.ok) {

            throw new Error(
                data.reply ||
                "Something went wrong."
            );

        }


        addMessage(
            data.reply ||
            "I couldn't generate a response.",
            "ai"
        );


    } catch (error) {

        console.error(error);

        addMessage(
            "Sorry, I couldn't connect to Gemini right now. Please check your API key and server.",
            "ai"
        );

    } finally {

        typing.style.display = "none";

        sendButton.disabled = false;

        input.focus();

    }

});


/* ENTER TO SEND */

input.addEventListener("keydown", function(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        form.requestSubmit();

    }

});


/* AUTO RESIZE */

input.addEventListener("input", function() {

    this.style.height = "auto";

    this.style.height =
        Math.min(this.scrollHeight, 140) + "px";

});