async function displayInput() {
    const topic = document.getElementById("userInput").value.trim();
    const outputElement = document.getElementById("output");

    if (!topic) {
        outputElement.innerText = "Please enter a valid topic.";
        return;
    }

    try {
        const response = await fetch("/create-video/", {  // Relative path to support different deployments
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Unknown error occurred.");
        }

        const data = await response.json();
        outputElement.innerHTML = `<a href="${data.video_url}" target="_blank">Watch Video</a>`;
    } catch (error) {
        console.error("Error:", error);
        outputElement.innerText = `Error: ${error.message}`;
    }
}
