

const API_URL = "http://127.0.0.1:8000";

const USER_ID_STORAGE_KEY =
    "egovassist_user_id";

const ACTIVE_CONVERSATION_STORAGE_KEY =
    "egovassist_active_conversation_id";

const body =
    document.body;

const themeToggle =
    document.getElementById("themeToggle");

const chatInput =
    document.getElementById("chatInput");

const actionBtn =
    document.getElementById("actionBtn");

const chatWindow =
    document.getElementById("chatWindow");

const langSelector =
    document.getElementById("langSelector");

const chatHistory =
    document.getElementById("chatHistory");

let isAiResponding = false;

let activeConversationId =
    localStorage.getItem(
        ACTIVE_CONVERSATION_STORAGE_KEY
    );

let conversations = [];

function generateUserId() {

    if (
        window.crypto &&
        typeof window.crypto.randomUUID ===
            "function"
    ) {
        return window.crypto.randomUUID();
    }

    return (
        "user-" +
        Date.now().toString(36) +
        "-" +
        Math.random()
            .toString(36)
            .substring(2, 12)
    );
}

function getUserId() {

    let userId =
        localStorage.getItem(
            USER_ID_STORAGE_KEY
        );

    if (!userId) {

        userId =
            generateUserId();

        localStorage.setItem(
            USER_ID_STORAGE_KEY,
            userId
        );
    }

    return userId;
}

const USER_ID =
    getUserId();

async function apiRequest(
    path,
    options = {}
) {

    const response =
        await fetch(
            `${API_URL}${path}`,
            {
                ...options,

                headers: {
                    "Content-Type":
                        "application/json",

                    ...(options.headers || {})
                }
            }
        );

    if (!response.ok) {

        let errorMessage =
            `Backend returned HTTP ${response.status}`;

        try {

            const errorData =
                await response.json();

            if (
                errorData &&
                errorData.detail
            ) {
                errorMessage =
                    errorData.detail;
            }

        }
        catch (_) {
            
        }

        throw new Error(
            errorMessage
        );
    }

    return response.json();
}

const AI_PROCESS_STAGES = [

    {
        id: "fetching",
        text: "Fetching Official Documents...",
        minTime: 900
    },

    {
        id: "extracting",
        text: "Extracting Relevant Information...",
        minTime: 1100
    },

    {
        id: "verifying",
        text: "Verifying Sources & Citations...",
        minTime: 1300
    },

    {
        id: "generating",
        text: "Generating Answer...",
        minTime: 1800
    },

    {
        id: "finalizing",
        text: "Final Touches...",
        minTime: 900
    }
];

function createAiStatusMessage() {

    const statusDiv =
        document.createElement("div");

    statusDiv.className =
        "ai-status-message";

    statusDiv.innerHTML = `
        <span class="ai-status-indicator">
            <span class="ai-status-dots">
                <span></span>
                <span></span>
                <span></span>
            </span>
        </span>

        <span class="ai-status-text">
            Fetching Official Documents...
        </span>
    `;

    chatWindow.appendChild(
        statusDiv
    );

    requestAnimationFrame(
        () => {

            chatWindow.scrollTop =
                chatWindow.scrollHeight;
        }
    );

    return statusDiv;
}

function changeAiStatus(
    statusDiv,
    text
) {

    if (
        !statusDiv ||
        !statusDiv.isConnected
    ) {
        return;
    }

    const textElement =
        statusDiv.querySelector(
            ".ai-status-text"
        );

    if (!textElement) {
        return;
    }

    textElement.classList.add(
        "status-changing"
    );

    setTimeout(
        () => {

            if (
                !statusDiv ||
                !statusDiv.isConnected
            ) {
                return;
            }

            textElement.textContent =
                text;

            textElement.classList.remove(
                "status-changing"
            );

        },
        180
    );
}

function startAiStatusAnimation(
    statusDiv
) {

    if (!statusDiv) {
        return null;
    }

    let currentStage = 0;

    let stageTimer = null;

    let completed = false;

    const advanceStage = () => {

        if (
            completed ||
            !statusDiv ||
            !statusDiv.isConnected
        ) {
            return;
        }

        if (
            currentStage >=
            AI_PROCESS_STAGES.length - 1
        ) {
            return;
        }

        currentStage++;

        changeAiStatus(
            statusDiv,
            AI_PROCESS_STAGES[
                currentStage
            ].text
        );

        scheduleNextStage();
    };

    const scheduleNextStage = () => {

        if (
            completed ||
            !statusDiv ||
            !statusDiv.isConnected
        ) {
            return;
        }

        const stage =
            AI_PROCESS_STAGES[
                currentStage
            ];

        stageTimer =
            setTimeout(
                advanceStage,
                stage.minTime
            );
    };

    scheduleNextStage();

    return {

        stop: () => {

            completed = true;

            if (stageTimer) {

                clearTimeout(
                    stageTimer
                );

                stageTimer = null;
            }
        },

        getCurrentStage: () =>
            currentStage
    };
}

async function finishAiStatusAnimation(
    statusDiv,
    statusController
) {

    if (statusController) {
        statusController.stop();
    }

    if (
        !statusDiv ||
        !statusDiv.isConnected
    ) {
        return;
    }

    changeAiStatus(
        statusDiv,
        "Generated."
    );

    await new Promise(
        (resolve) => {

            setTimeout(
                resolve,
                650
            );
        }
    );

    if (
        statusDiv &&
        statusDiv.isConnected
    ) {
        statusDiv.remove();
    }
}

function validateDom() {

    const requiredElements = {

        body,

        themeToggle,

        chatInput,

        actionBtn,

        chatWindow,

        langSelector,

        chatHistory
    };

    for (
        const [name, element]
        of Object.entries(
            requiredElements
        )
    ) {

        if (!element) {

            console.error(
                `eGovAssist startup error: Missing DOM element "${name}".`
            );

            return false;
        }
    }

    return true;
}

function debugSeparator(title) {

    console.log("");

    console.log(
        "===================================================="
    );

    console.log(title);

    console.log(
        "===================================================="
    );
}

function updateThemeIcon() {

    if (
        body.classList.contains(
            "dark-theme"
        )
    ) {

        themeToggle.innerHTML =
            '<i class="fa-solid fa-sun"></i>';

        themeToggle.title =
            "Switch to Light Mode";
    }

    else {

        themeToggle.innerHTML =
            '<i class="fa-solid fa-moon"></i>';

        themeToggle.title =
            "Switch to Dark Mode";
    }
}

function toggleTheme() {

    if (
        body.classList.contains(
            "light-theme"
        )
    ) {

        body.classList.replace(
            "light-theme",
            "dark-theme"
        );
    }

    else {

        body.classList.replace(
            "dark-theme",
            "light-theme"
        );
    }

    updateThemeIcon();
}

themeToggle.addEventListener(
    "click",
    toggleTheme
);

function updateButtonIcon() {

    if (isAiResponding) {

        actionBtn.innerHTML =
            '<i class="fa-solid fa-spinner fa-spin"></i>';

        actionBtn.title =
            "AI is responding";

        return;
    }

    if (
        chatInput.value.trim() === ""
    ) {

        actionBtn.innerHTML =
            '<i class="fa-solid fa-microphone"></i>';

        actionBtn.title =
            "Voice Input";
    }

    else {

        actionBtn.innerHTML =
            '<i class="fa-solid fa-paper-plane"></i>';

        actionBtn.title =
            "Send Prompt";
    }
}

chatInput.addEventListener(
    "input",
    updateButtonIcon
);

function convertEvidenceReferences(
    html
) {

    const evidencePattern =
        /\[\s*EVIDENCE\s+(\d+)\s*\]/gi;

    return html.replace(
        evidencePattern,
        '<button type="button" class="evidence-ref" ' +
        'data-evidence-number="$1" ' +
        'aria-expanded="false" ' +
        'title="View evidence $1">' +
        'Evidence $1' +
        '</button>'
    );
}

function renderAiMessage(
    msgDiv,
    text,
    evidence = []
) {

    const originalText =
        String(text ?? "");

    if (
        typeof marked ===
        "undefined"
    ) {

        msgDiv.textContent =
            originalText;

        msgDiv._evidence =
            Array.isArray(evidence)
                ? evidence
                : [];

        return;
    }

    if (
        typeof DOMPurify ===
        "undefined"
    ) {

        msgDiv.textContent =
            originalText;

        msgDiv._evidence =
            Array.isArray(evidence)
                ? evidence
                : [];

        return;
    }

    let renderedMarkdown;

    try {

        renderedMarkdown =
            marked.parse(
                originalText,
                {
                    breaks: true,
                    gfm: true
                }
            );

    }

    catch (error) {

        console.error(
            "Markdown rendering failed:",
            error
        );

        msgDiv.textContent =
            originalText;

        msgDiv._evidence =
            Array.isArray(evidence)
                ? evidence
                : [];

        return;
    }

    let safeHtml;

    try {

        safeHtml =
            DOMPurify.sanitize(
                renderedMarkdown
            );

    }

    catch (error) {

        console.error(
            "DOM sanitization failed:",
            error
        );

        msgDiv.textContent =
            originalText;

        msgDiv._evidence =
            Array.isArray(evidence)
                ? evidence
                : [];

        return;
    }

    const finalHtml =
        convertEvidenceReferences(
            safeHtml
        );

    msgDiv.innerHTML =
        finalHtml;

    msgDiv._evidence =
        Array.isArray(evidence)
            ? evidence
            : [];
}

function appendMessage(
    text,
    sender,
    evidence = []
) {

    const msgDiv =
        document.createElement("div");

    msgDiv.classList.add(
        "message",
        sender
    );

    if (
        sender === "ai"
    ) {

        renderAiMessage(
            msgDiv,
            text,
            evidence
        );

    }

    else {

        msgDiv.textContent =
            String(text ?? "");
    }

    chatWindow.appendChild(
        msgDiv
    );

    requestAnimationFrame(
        () => {

            chatWindow.scrollTop =
                chatWindow.scrollHeight;
        }
    );

    return msgDiv;
}

function clearChatWindow() {

    chatWindow.innerHTML = "";
}

function getEvidenceByNumber(
    messageElement,
    number
) {

    const evidence =
        Array.isArray(
            messageElement._evidence
        )
            ? messageElement._evidence
            : [];

    return evidence.find(
        (item) =>
            Number(item.number) ===
            Number(number)
    );
}

function getEvidenceSummary(
    evidence
) {

    if (!evidence) {
        return "";
    }

    const summary =
        evidence.excerpt ||
        evidence.summary ||
        evidence.description ||
        "";

    return String(
        summary
    ).trim();
}

function removeEvidencePanel(
    messageElement
) {

    const existingPanel =
        messageElement.querySelector(
            ".evidence-panel"
        );

    if (existingPanel) {
        existingPanel.remove();
    }

    messageElement
        .querySelectorAll(
            ".evidence-ref"
        )
        .forEach(
            (button) => {

                button.setAttribute(
                    "aria-expanded",
                    "false"
                );
            }
        );
}

function setSafeMarkdown(
    element,
    text
) {

    const value =
        String(
            text ?? ""
        );

    if (
        typeof marked ===
            "undefined" ||
        typeof DOMPurify ===
            "undefined"
    ) {

        element.textContent =
            value;

        return;
    }

    try {

        const html =
            marked.parse(
                value,
                {
                    breaks: true,
                    gfm: true
                }
            );

        element.innerHTML =
            DOMPurify.sanitize(
                html
            );

    }

    catch (error) {

        console.error(
            "Evidence Markdown rendering failed:",
            error
        );

        element.textContent =
            value;
    }
}

function escapeHtml(
    value
) {

    return String(
        value ?? ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}

function buildEvidenceViewerHtml(
    evidence,
    locator
) {

    if (!evidence) {
        return "";
    }

    const resolvedLocator =
        locator &&
        typeof locator === "object"
            ? locator
            : {};

    const title =
        evidence.title ||
        evidence.document ||
        evidence.source_name ||
        "Government Source";

    const issuer =
        evidence.issuer ||
        "Government / Official Web Source";

    const authority =
        evidence.authority ||
        "Primary / Official";

    const verificationStatus =
        evidence.verification_status ||
        "verified";

    const trustScore =
        evidence.trust_score !== null &&
        evidence.trust_score !== undefined &&
        evidence.trust_score !== ""
            ? `Trust: ${escapeHtml(evidence.trust_score)}`
            : "Trust score unavailable";

    const exactSection =
        resolvedLocator.section_title ||
        resolvedLocator.section ||
        evidence.section ||
        "";

    const exactPage =
        resolvedLocator.page ??
        (
            Array.isArray(
                resolvedLocator.pages
            ) &&
            resolvedLocator.pages.length > 0
                ? resolvedLocator.pages[0]
                : evidence.page
        );

    const exactText =
        resolvedLocator.paragraph_text ||
        resolvedLocator.matched_text ||
        resolvedLocator.requested_excerpt ||
        getEvidenceSummary(evidence);

    const confidence =
        resolvedLocator.confidence !== null &&
        resolvedLocator.confidence !== undefined &&
        resolvedLocator.confidence !== ""
            ? resolvedLocator.confidence
            : null;

    const sourceUrl =
        resolvedLocator.page_url ||
        resolvedLocator.direct_url ||
        resolvedLocator.source_url ||
        evidence.source_url ||
        "";

    const safeTitle =
        escapeHtml(title);

    const safeIssuer =
        escapeHtml(issuer);

    const safeAuthority =
        escapeHtml(authority);

    const safeStatus =
        escapeHtml(
            String(
                verificationStatus
            ).replaceAll(
                "_",
                " "
            )
        );

    const safeSection =
        escapeHtml(
            exactSection
        );

    const safePage =
        exactPage !== null &&
        exactPage !== undefined &&
        exactPage !== ""
            ? escapeHtml(exactPage)
            : "";

    const safeText =
        escapeHtml(
            exactText
        );

    const safeConfidence =
        confidence !== null
            ? escapeHtml(confidence)
            : "";

    const safeSourceUrl =
        escapeHtml(
            sourceUrl
        );

    const locationParts = [];

    if (safeSection) {
        locationParts.push(
            `<span><strong>Section:</strong> ${safeSection}</span>`
        );
    }

    if (safePage) {
        locationParts.push(
            `<span><strong>Page:</strong> ${safePage}</span>`
        );
    }

    const originalSourceButton =
        sourceUrl
            ? `
                <a
                    class="source-open-button"
                    href="${safeSourceUrl}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    Open original source
                </a>
            `
            : "";

    const confidenceHtml =
        confidence !== null
            ? `
                <div class="viewer-confidence">
                    Location confidence: ${safeConfidence}
                </div>
            `
            : "";

    return `
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Evidence ${escapeHtml(evidence.number)} - ${safeTitle}
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Helvetica,
                Arial,
                sans-serif;
            background: #f7f8fa;
            color: #252525;
        }

        .viewer-shell {
            width: 100%;
            max-width: 920px;
            margin: 0 auto;
            padding: 40px 24px 60px;
        }

        .viewer-header {
            margin-bottom: 24px;
        }

        .viewer-back {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border: none;
            background: transparent;
            color: #0056b3;
            cursor: pointer;
            font: inherit;
            font-weight: 600;
            padding: 0;
            margin-bottom: 22px;
        }

        .viewer-card {
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 16px;
            padding: 26px;
            box-shadow:
                0 8px 30px rgba(0, 0, 0, 0.06);
        }

        .viewer-evidence-number {
            display: inline-flex;
            align-items: center;
            padding: 5px 9px;
            border-radius: 7px;
            background: #e3f2fd;
            color: #0056b3;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 12px;
        }

        .viewer-title {
            margin: 0 0 18px;
            font-size: 24px;
            line-height: 1.35;
        }

        .viewer-meta {
            display: grid;
            gap: 7px;
            margin-bottom: 18px;
            color: #666666;
            font-size: 14px;
        }

        .viewer-verification {
            display: inline-flex;
            width: fit-content;
            padding: 6px 9px;
            border-radius: 7px;
            background: #eeeeee;
            color: #252525;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 26px;
        }

        .viewer-divider {
            height: 1px;
            background: #e0e0e0;
            margin: 0 0 26px;
        }

        .viewer-section-title {
            margin: 0 0 9px;
            font-size: 14px;
            font-weight: 700;
        }

        .viewer-location {
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            margin-bottom: 20px;
            color: #666666;
            font-size: 13px;
        }

        .viewer-passage {
            margin: 0;
            padding: 17px 18px;
            border-left: 4px solid #0056b3;
            border-radius: 0 9px 9px 0;
            background: #f1f1f1;
            color: #252525;
            font-size: 15px;
            line-height: 1.7;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        .viewer-confidence {
            margin-top: 12px;
            color: #777777;
            font-size: 12px;
        }

        .viewer-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 28px;
        }

        .source-open-button {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 9px;
            background: #0056b3;
            color: #ffffff;
            text-decoration: none;
            font-size: 13px;
            font-weight: 700;
        }

        .source-open-button:hover {
            opacity: 0.9;
        }

        @media (max-width: 640px) {

            .viewer-shell {
                padding: 24px 14px 40px;
            }

            .viewer-card {
                padding: 20px;
            }

            .viewer-title {
                font-size: 20px;
            }

        }

    </style>

    <link
        rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css"
    >

</head>

<body>

    <main class="viewer-shell">

        <div class="viewer-header">

            <button
                class="viewer-back"
                type="button"
                onclick="window.close()"
            >
                <i class="fa-solid fa-arrow-left"></i>
                Close evidence
            </button>

        </div>

        <section class="viewer-card">

            <div class="viewer-evidence-number">
                Evidence ${escapeHtml(evidence.number)}
            </div>

            <h1 class="viewer-title">
                ${safeTitle}
            </h1>

            <div class="viewer-meta">

                <div>
                    <strong>Issuer:</strong>
                    ${safeIssuer}
                </div>

                <div>
                    <strong>Authority:</strong>
                    ${safeAuthority}
                </div>

            </div>

            <div class="viewer-verification">
                ${safeStatus}
                &nbsp; • &nbsp;
                ${trustScore}
            </div>

            <div class="viewer-divider"></div>

            ${
                locationParts.length > 0
                    ? `
                        <h2 class="viewer-section-title">
                            Exact location
                        </h2>

                        <div class="viewer-location">
                            ${locationParts.join("")}
                        </div>
                    `
                    : ""
            }

            <h2 class="viewer-section-title">
                Relevant information from the source
            </h2>

            <blockquote class="viewer-passage">
                ${safeText}
            </blockquote>

            ${confidenceHtml}

            ${
                originalSourceButton
                    ? `
                        <div class="viewer-actions">
                            ${originalSourceButton}
                        </div>
                    `
                    : ""
            }

        </section>

    </main>

</body>

</html>
    `;
}

function openEvidenceViewer(
    evidence,
    locator,
    existingWindow = null
) {

    if (!evidence) {
        return null;
    }

    const viewerHtml =
        buildEvidenceViewerHtml(
            evidence,
            locator
        );

    let viewerWindow =
        existingWindow;

    if (
        !viewerWindow ||
        viewerWindow.closed
    ) {

        viewerWindow =
            window.open(
                "",
                "_blank"
            );
    }

    if (!viewerWindow) {

        return null;
    }

    try {

        try {

            viewerWindow.opener =
                null;

        }

        catch (_) {
            
        }

        viewerWindow.document.open();

        viewerWindow.document.write(
            viewerHtml
        );

        viewerWindow.document.close();

        viewerWindow.focus();

    }

    catch (error) {

        console.error(
            "Failed to render evidence viewer:",
            error
        );

        try {

            viewerWindow.document.body.innerHTML = `
                <div style="
                    font-family: sans-serif;
                    padding: 40px;
                    color: #252525;
                ">
                    <h2>
                        Evidence viewer could not be rendered.
                    </h2>

                    <p>
                        Please close this tab and try again.
                    </p>
                </div>
            `;

        }

        catch (_) {
            
        }
    }

    return viewerWindow;
}

function showEvidenceViewerLoading(
    viewerWindow,
    evidence
) {

    if (
        !viewerWindow ||
        viewerWindow.closed
    ) {
        return;
    }

    const evidenceNumber =
        evidence &&
        evidence.number !== undefined
            ? escapeHtml(evidence.number)
            : "";

    const title =
        evidence &&
        (
            evidence.title ||
            evidence.document ||
            evidence.source_name
        )
            ? escapeHtml(
                evidence.title ||
                evidence.document ||
                evidence.source_name
            )
            : "Government Source";

    try {

        viewerWindow.document.open();

        viewerWindow.document.write(`
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Evidence ${evidenceNumber} - ${title}
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Helvetica,
                Arial,
                sans-serif;
            background: #f7f8fa;
            color: #252525;
        }

        .loading-card {
            width: 100%;
            max-width: 520px;
            padding: 32px;
            text-align: center;
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 16px;
            box-shadow:
                0 8px 30px rgba(0, 0, 0, 0.06);
        }

        .spinner {
            width: 38px;
            height: 38px;
            margin: 0 auto 20px;
            border: 4px solid #e5e5e5;
            border-top-color: #0056b3;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        h1 {
            margin: 0 0 10px;
            font-size: 21px;
        }

        p {
            margin: 0;
            color: #666666;
            line-height: 1.6;
        }

        @keyframes spin {

            to {
                transform: rotate(360deg);
            }

        }

    </style>

</head>

<body>

    <main class="loading-card">

        <div class="spinner"></div>

        <h1>
            Locating exact source...
        </h1>

        <p>
            eGovAssist is verifying the exact location
            of the supporting information.
        </p>

    </main>

</body>

</html>
        `);

        viewerWindow.document.close();

    }

    catch (error) {

        console.error(
            "Failed to show evidence loading page:",
            error
        );
    }
}

function showEvidenceViewerError(
    viewerWindow,
    message
) {

    if (
        !viewerWindow ||
        viewerWindow.closed
    ) {
        return;
    }

    const safeMessage =
        escapeHtml(
            message ||
            "The exact source could not be located."
        );

    try {

        viewerWindow.document.open();

        viewerWindow.document.write(`
<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        Evidence Viewer
    </title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Roboto,
                Helvetica,
                Arial,
                sans-serif;
            background: #f7f8fa;
            color: #252525;
        }

        .error-card {
            width: 100%;
            max-width: 620px;
            padding: 32px;
            background: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 16px;
            box-shadow:
                0 8px 30px rgba(0, 0, 0, 0.06);
        }

        .error-icon {
            width: 46px;
            height: 46px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: #eeeeee;
            font-size: 22px;
        }

        h1 {
            margin: 0 0 12px;
            font-size: 22px;
        }

        p {
            margin: 0;
            color: #666666;
            line-height: 1.65;
        }

        .close-button {
            margin-top: 24px;
            padding: 10px 15px;
            border: none;
            border-radius: 9px;
            background: #0056b3;
            color: #ffffff;
            cursor: pointer;
            font-size: 13px;
            font-weight: 700;
        }

    </style>

</head>

<body>

    <main class="error-card">

        <div class="error-icon">
            !
        </div>

        <h1>
            Exact source could not be located
        </h1>

        <p>
            ${safeMessage}
        </p>

        <button
            type="button"
            class="close-button"
            onclick="window.close()"
        >
            Close evidence
        </button>

    </main>

</body>

</html>
        `);

        viewerWindow.document.close();

    }

    catch (error) {

        console.error(
            "Failed to show evidence error page:",
            error
        );
    }
}

function createExactSourceButton(
    messageElement,
    evidence,
    panel
) {

    const button =
        document.createElement(
            "button"
        );

    button.type =
        "button";

    button.className =
        "evidence-expand-button";

    button.innerHTML = `
        <i class="fa-solid fa-up-right-from-square"></i>
        <span>Open exact source</span>
    `;

    button.setAttribute(
        "aria-expanded",
        "false"
    );

    button.addEventListener(
        "click",
        async () => {

            if (
                button.disabled
            ) {
                return;
            }

            const sourceUrl =
                typeof evidence.source_url ===
                    "string"
                    ? evidence.source_url.trim()
                    : "";

            const excerpt =
                getEvidenceSummary(
                    evidence
                );

            if (!sourceUrl) {

                showExactSourceError(
                    panel,
                    "An exact source cannot be located because this evidence does not contain a supported source URL."
                );

                return;
            }

            if (!excerpt) {

                showExactSourceError(
                    panel,
                    "An exact source cannot be located because this evidence does not contain the supporting passage."
                );

                return;
            }

            const viewerWindow =
                window.open(
                    "",
                    "_blank"
                );

            if (!viewerWindow) {

                console.error(
                    "Evidence popup was blocked by the browser."
                );

                alert(
                    "The evidence page could not be opened. Please allow pop-ups for eGovAssist and try again."
                );

                return;
            }

            showEvidenceViewerLoading(
                viewerWindow,
                evidence
            );

            button.disabled =
                true;

            button.setAttribute(
                "aria-busy",
                "true"
            );

            button.innerHTML = `
                <i class="fa-solid fa-spinner fa-spin"></i>
                <span>Locating exact source...</span>
            `;

            try {

                const result =
                    await apiRequest(
                        "/evidence/locate",
                        {
                            method: "POST",

                            body:
                                JSON.stringify({

                                    source_url:
                                        sourceUrl,

                                    excerpt:
                                        excerpt,

                                    chunk_id:
                                        evidence.chunk_id ||
                                        "",

                                    page:
                                        evidence.page ??
                                        null,

                                    section:
                                        evidence.section ||
                                        "",

                                    title:
                                        evidence.title ||
                                        evidence.document ||
                                        "",

                                    source_type:
                                        evidence.source_type ||
                                        ""
                                })
                        }
                    );

                const locator =
                    result &&
                    result.locator
                        ? result.locator
                        : result;

                const renderedWindow =
                    openEvidenceViewer(
                        evidence,
                        locator,
                        viewerWindow
                    );

                if (!renderedWindow) {

                    throw new Error(
                        "The evidence viewer could not be rendered."
                    );
                }

                button.setAttribute(
                    "aria-expanded",
                    "true"
                );

                button.innerHTML = `
                    <i class="fa-solid fa-arrow-up-right-from-square"></i>
                    <span>Open exact source</span>
                `;

            }

            catch (error) {

                console.error(
                    "Exact evidence lookup failed:",
                    error
                );

                const errorMessage =
                    error &&
                    error.message
                        ? error.message
                        : "The exact source could not be located.";

                showEvidenceViewerError(
                    viewerWindow,
                    errorMessage
                );

                showExactSourceError(
                    panel,
                    errorMessage
                );

                button.setAttribute(
                    "aria-expanded",
                    "false"
                );

                button.innerHTML = `
                    <i class="fa-solid fa-up-right-from-square"></i>
                    <span>Retry exact source</span>
                `;
            }

            finally {

                button.disabled =
                    false;

                button.removeAttribute(
                    "aria-busy"
                );
            }
        }
    );

    return button;
}

function showExactSourceError(
    panel,
    message
) {

    const previous =
        panel.querySelector(
            ".exact-source-error"
        );

    if (previous) {
        previous.remove();
    }

    const error =
        document.createElement(
            "div"
        );

    error.className =
        "exact-source-error";

    error.textContent =
        message;

    panel.appendChild(
        error
    );
}

function createEvidencePanel(
    messageElement,
    evidence,
    triggerButton
) {

    removeEvidencePanel(
        messageElement
    );

    const panel =
        document.createElement(
            "div"
        );

    panel.className =
        "evidence-panel";

    panel.dataset.evidenceNumber =
        String(
            evidence.number
        );

    const header =
        document.createElement(
            "div"
        );

    header.className =
        "evidence-panel-header";

    const title =
        document.createElement(
            "strong"
        );

    title.textContent =
        `Evidence ${evidence.number}`;

    const closeButton =
        document.createElement(
            "button"
        );

    closeButton.type =
        "button";

    closeButton.className =
        "evidence-close";

    closeButton.setAttribute(
        "aria-label",
        "Close evidence"
    );

    closeButton.innerHTML =
        '<i class="fa-solid fa-xmark"></i>';

    closeButton.addEventListener(
        "click",
        () =>
            removeEvidencePanel(
                messageElement
            )
    );

    header.appendChild(
        title
    );

    header.appendChild(
        closeButton
    );

    panel.appendChild(
        header
    );

    const sourceName =
        evidence.title ||
        evidence.document ||
        evidence.source_name ||
        "Government document";

    const sourceElement =
        document.createElement(
            "div"
        );

    sourceElement.className =
        "evidence-source";

    sourceElement.textContent =
        sourceName;

    panel.appendChild(
        sourceElement
    );

    if (
        evidence.issuer
    ) {

        const issuer =
            document.createElement(
                "div"
            );

        issuer.className =
            "evidence-meta";

        issuer.textContent =
            `Issuer: ${evidence.issuer}`;

        panel.appendChild(
            issuer
        );
    }

    const locationParts = [];

    if (
        evidence.section
    ) {

        locationParts.push(
            `Section: ${evidence.section}`
        );
    }

    if (
        evidence.page !== null &&
        evidence.page !== undefined &&
        evidence.page !== ""
    ) {

        locationParts.push(
            `Page: ${evidence.page}`
        );
    }

    if (
        locationParts.length
    ) {

        const location =
            document.createElement(
                "div"
            );

        location.className =
            "evidence-meta";

        location.textContent =
            locationParts.join(
                " • "
            );

        panel.appendChild(
            location
        );
    }

    if (
        evidence.authority
    ) {

        const authority =
            document.createElement(
                "div"
            );

        authority.className =
            "evidence-meta";

        authority.textContent =
            `Authority: ${evidence.authority}`;

        panel.appendChild(
            authority
        );
    }

    const verificationRow =
        document.createElement(
            "div"
        );

    verificationRow.className =
        "evidence-verification";

    const status =
        evidence.verification_status ||
        "unknown";

    const score =
        evidence.trust_score !== null &&
        evidence.trust_score !== undefined &&
        evidence.trust_score !== ""
            ? `Trust: ${evidence.trust_score}`
            : "Trust score unavailable";

    verificationRow.textContent =
        `${String(
            status
        ).replaceAll(
            "_",
            " "
        )} • ${score}`;

    panel.appendChild(
        verificationRow
    );

    const summaryText =
        getEvidenceSummary(
            evidence
        );

    if (
        summaryText
    ) {

        const label =
            document.createElement(
                "div"
            );

        label.className =
            "evidence-excerpt-label";

        label.textContent =
            "Relevant summary";

        panel.appendChild(
            label
        );

        const excerpt =
            document.createElement(
                "blockquote"
            );

        excerpt.className =
            "evidence-excerpt";

        setSafeMarkdown(
            excerpt,
            summaryText
        );

        panel.appendChild(
            excerpt
        );
    }

    const exactSourceButton =
        createExactSourceButton(
            messageElement,
            evidence,
            panel
        );

    panel.appendChild(
        exactSourceButton
    );

    messageElement.appendChild(
        panel
    );

    triggerButton.setAttribute(
        "aria-expanded",
        "true"
    );

    requestAnimationFrame(
        () => {

            panel.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });
        }
    );
}

chatWindow.addEventListener(
    "click",
    (event) => {

        const button =
            event.target.closest(
                ".evidence-ref"
            );

        if (!button) {
            return;
        }

        const messageElement =
            button.closest(
                ".message.ai"
            );

        if (!messageElement) {
            return;
        }

        const number =
            button.dataset.evidenceNumber;

        const evidence =
            getEvidenceByNumber(
                messageElement,
                number
            );

        if (!evidence) {

            console.warn(
                `Evidence ${number} was referenced by the answer but was not returned by the backend.`
            );

            return;
        }

        const panel =
            messageElement.querySelector(
                ".evidence-panel"
            );

        const isSameEvidenceOpen =
            panel &&
            panel.dataset.evidenceNumber ===
                String(number);

        if (
            isSameEvidenceOpen
        ) {

            removeEvidencePanel(
                messageElement
            );

            return;
        }

        createEvidencePanel(
            messageElement,
            evidence,
            button
        );
    }
);

function getConversationTitle(
    conversation
) {

    if (
        conversation &&
        conversation.title &&
        conversation.title.trim()
    ) {

        return conversation.title.trim();
    }

    return "New Chat";
}

function renderConversationHistory() {

    if (!chatHistory) {
        return;
    }

    chatHistory.innerHTML = "";

    if (
        conversations.length === 0
    ) {

        const empty =
            document.createElement(
                "div"
            );

        empty.className =
            "chat-history-empty";

        empty.textContent =
            "No previous chats";

        chatHistory.appendChild(
            empty
        );

        return;
    }

    conversations.forEach(
        (conversation) => {

            const item =
                document.createElement(
                    "button"
                );

            item.type =
                "button";

            item.className =
                "chat-history-item";

            if (
                conversation.id ===
                activeConversationId
            ) {

                item.classList.add(
                    "active"
                );
            }

            item.dataset.conversationId =
                conversation.id;

            const title =
                document.createElement(
                    "span"
                );

            title.className =
                "chat-history-title";

            title.textContent =
                getConversationTitle(
                    conversation
                );

            item.appendChild(
                title
            );

            if (
                conversation.pinned
            ) {

                const pin =
                    document.createElement(
                        "i"
                    );

                pin.className =
                    "fa-solid fa-thumbtack";

                pin.title =
                    "Pinned";

                item.appendChild(
                    pin
                );
            }

            item.addEventListener(
                "click",
                () => {

                    loadConversation(
                        conversation.id
                    );
                }
            );

            item.addEventListener(
                "contextmenu",
                (event) => {

                    event.preventDefault();

                    showConversationContextMenu(
                        event.clientX,
                        event.clientY,
                        conversation
                    );
                }
            );

            chatHistory.appendChild(
                item
            );
        }
    );
}

let activeContextConversation = null;

let conversationContextMenu = null;

function createConversationContextMenu() {

    if (
        conversationContextMenu
    ) {
        return conversationContextMenu;
    }

    const menu =
        document.createElement(
            "div"
        );

    menu.className =
        "conversation-context-menu";

    menu.style.position =
        "fixed";

    menu.style.zIndex =
        "99999";

    menu.style.minWidth =
        "170px";

    menu.style.padding =
        "6px";

    menu.style.borderRadius =
        "10px";

    menu.style.display =
        "none";

    menu.style.background =
        "var(--card-bg, #ffffff)";

    menu.style.border =
        "1px solid rgba(128,128,128,0.25)";

    menu.style.boxShadow =
        "0 8px 30px rgba(0,0,0,0.15)";

    const renameButton =
        document.createElement(
            "button"
        );

    renameButton.type =
        "button";

    renameButton.className =
        "conversation-context-item";

    renameButton.innerHTML = `
        <i class="fa-solid fa-pen"></i>
        <span>Rename</span>
    `;

    renameButton.style.display =
        "flex";

    renameButton.style.alignItems =
        "center";

    renameButton.style.gap =
        "10px";

    renameButton.style.width =
        "100%";

    renameButton.style.border =
        "none";

    renameButton.style.background =
        "transparent";

    renameButton.style.padding =
        "9px 10px";

    renameButton.style.borderRadius =
        "7px";

    renameButton.style.cursor =
        "pointer";

    renameButton.style.textAlign =
        "left";

    renameButton.addEventListener(
        "click",
        async () => {

            if (
                !activeContextConversation
            ) {
                return;
            }

            const conversation =
                activeContextConversation;

            hideConversationContextMenu();

            await renameConversation(
                conversation
            );
        }
    );

    const deleteButton =
        document.createElement(
            "button"
        );

    deleteButton.type =
        "button";

    deleteButton.className =
        "conversation-context-item conversation-context-delete";

    deleteButton.innerHTML = `
        <i class="fa-solid fa-trash"></i>
        <span>Delete</span>
    `;

    deleteButton.style.display =
        "flex";

    deleteButton.style.alignItems =
        "center";

    deleteButton.style.gap =
        "10px";

    deleteButton.style.width =
        "100%";

    deleteButton.style.border =
        "none";

    deleteButton.style.background =
        "transparent";

    deleteButton.style.padding =
        "9px 10px";

    deleteButton.style.borderRadius =
        "7px";

    deleteButton.style.cursor =
        "pointer";

    deleteButton.style.textAlign =
        "left";

    deleteButton.addEventListener(
        "click",
        async () => {

            if (
                !activeContextConversation
            ) {
                return;
            }

            const conversation =
                activeContextConversation;

            hideConversationContextMenu();

            await deleteConversationFromHistory(
                conversation
            );
        }
    );

    menu.appendChild(
        renameButton
    );

    menu.appendChild(
        deleteButton
    );

    document.body.appendChild(
        menu
    );

    conversationContextMenu =
        menu;

    return menu;
}

function showConversationContextMenu(
    x,
    y,
    conversation
) {

    const menu =
        createConversationContextMenu();

    activeContextConversation =
        conversation;

    menu.style.display =
        "block";

    const menuWidth =
        180;

    const menuHeight =
        95;

    const safeX =
        Math.min(
            x,
            window.innerWidth -
                menuWidth -
                10
        );

    const safeY =
        Math.min(
            y,
            window.innerHeight -
                menuHeight -
                10
        );

    menu.style.left =
        `${Math.max(10, safeX)}px`;

    menu.style.top =
        `${Math.max(10, safeY)}px`;
}

function hideConversationContextMenu() {

    if (
        conversationContextMenu
    ) {

        conversationContextMenu.style.display =
            "none";
    }

    activeContextConversation =
        null;
}

document.addEventListener(
    "click",
    (event) => {

        if (
            conversationContextMenu &&
            !conversationContextMenu.contains(
                event.target
            )
        ) {

            hideConversationContextMenu();
        }
    }
);

document.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Escape"
        ) {

            hideConversationContextMenu();
        }
    }
);

async function renameConversation(
    conversation
) {

    if (
        !conversation ||
        !conversation.id
    ) {
        return;
    }

    const currentTitle =
        getConversationTitle(
            conversation
        );

    const newTitle =
        window.prompt(
            "Enter a new chat name:",
            currentTitle
        );

    if (
        newTitle === null
    ) {
        return;
    }

    const trimmedTitle =
        newTitle.trim();

    if (
        !trimmedTitle
    ) {

        alert(
            "Chat name cannot be empty."
        );

        return;
    }

    try {

        const data =
            await apiRequest(
                `/conversations/${encodeURIComponent(conversation.id)}`,
                {
                    method: "PATCH",

                    body:
                        JSON.stringify({
                            user_id:
                                USER_ID,

                            title:
                                trimmedTitle
                        })
                }
            );

        if (
            data &&
            data.conversation
        ) {

            conversations =
                conversations.map(
                    (item) =>
                        item.id ===
                        conversation.id
                            ? data.conversation
                            : item
                );
        }

        else {

            conversations =
                conversations.map(
                    (item) =>
                        item.id ===
                        conversation.id
                            ? {
                                ...item,
                                title:
                                    trimmedTitle
                            }
                            : item
                );
        }

        renderConversationHistory();

        console.log(
            "Conversation renamed:",
            conversation.id,
            trimmedTitle
        );

    }

    catch (error) {

        console.error(
            "Failed to rename conversation:",
            error
        );

        alert(
            "Could not rename this chat. Please try again."
        );
    }
}

async function deleteConversationFromHistory(
    conversation
) {

    if (
        !conversation ||
        !conversation.id
    ) {
        return;
    }

    const title =
        getConversationTitle(
            conversation
        );

    const confirmed =
        window.confirm(
            `Delete "${title}"?\n\nThis will permanently delete this conversation and its messages.`
        );

    if (
        !confirmed
    ) {
        return;
    }

    try {

        await apiRequest(
            `/conversations/${encodeURIComponent(conversation.id)}?user_id=${encodeURIComponent(USER_ID)}`,
            {
                method: "DELETE"
            }
        );

        conversations =
            conversations.filter(
                (item) =>
                    item.id !==
                    conversation.id
            );

        if (
            activeConversationId ===
            conversation.id
        ) {

            activeConversationId =
                null;

            localStorage.removeItem(
                ACTIVE_CONVERSATION_STORAGE_KEY
            );

            clearChatWindow();
        }

        renderConversationHistory();

        if (
            !activeConversationId
        ) {

            chatInput.focus();
        }

        console.log(
            "Conversation deleted:",
            conversation.id
        );

    }

    catch (error) {

        console.error(
            "Failed to delete conversation:",
            error
        );

        alert(
            "Could not delete this chat. Please try again."
        );
    }
}

async function loadConversationHistory() {

    try {

        const data =
            await apiRequest(
                `/conversations?user_id=${encodeURIComponent(USER_ID)}`
            );

        conversations =
            Array.isArray(
                data.conversations
            )
                ? data.conversations
                : [];

        renderConversationHistory();

        if (
            activeConversationId
        ) {

            const exists =
                conversations.some(
                    (conversation) =>
                        conversation.id ===
                        activeConversationId
                );

            if (exists) {

                await loadConversation(
                    activeConversationId,
                    false
                );

                return;
            }

            activeConversationId =
                null;

            localStorage.removeItem(
                ACTIVE_CONVERSATION_STORAGE_KEY
            );
        }

        clearChatWindow();

    }

    catch (error) {

        console.error(
            "Failed to load chat history:",
            error
        );
    }
}

async function loadConversation(
    conversationId,
    updateHistory = true
) {

    if (
        isAiResponding
    ) {
        return;
    }

    try {

        const data =
            await apiRequest(
                `/conversations/${encodeURIComponent(conversationId)}?user_id=${encodeURIComponent(USER_ID)}`
            );

        const conversation =
            data.conversation;

        if (!conversation) {

            throw new Error(
                "Conversation was not returned by the backend."
            );
        }

        activeConversationId =
            conversation.id;

        localStorage.setItem(
            ACTIVE_CONVERSATION_STORAGE_KEY,
            activeConversationId
        );

        clearChatWindow();

        const messages =
            Array.isArray(
                conversation.messages
            )
                ? conversation.messages
                : [];

        messages.forEach(
            (message) => {

                const sender =
                    message.role ===
                    "assistant"
                        ? "ai"
                        : "user";

                appendMessage(
                    message.content,
                    sender,
                    Array.isArray(
                        message.evidence
                    )
                        ? message.evidence
                        : []
                );
            }
        );

        if (
            updateHistory
        ) {

            renderConversationHistory();
        }

        requestAnimationFrame(
            () => {

                chatWindow.scrollTop =
                    chatWindow.scrollHeight;
            }
        );

    }

    catch (error) {

        console.error(
            "Failed to load conversation:",
            error
        );
    }
}

async function createNewChat() {

    if (
        isAiResponding
    ) {
        return;
    }

    try {

        const data =
            await apiRequest(
                "/conversations",
                {
                    method: "POST",

                    body:
                        JSON.stringify({
                            user_id:
                                USER_ID,

                            title:
                                "New Chat"
                        })
                }
            );

        const conversation =
            data.conversation;

        if (!conversation) {

            throw new Error(
                "Conversation creation failed."
            );
        }

        activeConversationId =
            conversation.id;

        localStorage.setItem(
            ACTIVE_CONVERSATION_STORAGE_KEY,
            activeConversationId
        );

        clearChatWindow();

        conversations =
            [
                conversation,
                ...conversations
            ];

        const seen =
            new Set();

        conversations =
            conversations.filter(
                (item) => {

                    if (
                        !item ||
                        !item.id ||
                        seen.has(item.id)
                    ) {
                        return false;
                    }

                    seen.add(
                        item.id
                    );

                    return true;
                }
            );

        renderConversationHistory();

        chatInput.focus();

        console.log(
            "New conversation created:",
            activeConversationId
        );

    }

    catch (error) {

        console.error(
            "Failed to create new chat:",
            error
        );

        alert(
            "Could not create a new chat. Please try again."
        );
    }
}

function findNewChatButton() {

    const possibleIds = [
        "newChat",
        "newChatBtn",
        "newConversation",
        "newConversationBtn"
    ];

    for (
        const id
        of possibleIds
    ) {

        const element =
            document.getElementById(
                id
            );

        if (element) {
            return element;
        }
    }

    return null;
}

function ensureNewChatButton() {

    let button =
        findNewChatButton();

    if (button) {

        button.addEventListener(
            "click",
            createNewChat
        );

        return button;
    }

    button =
        document.createElement(
            "button"
        );

    button.type =
        "button";

    button.id =
        "newChatBtn";

    button.className =
        "new-chat-btn";

    button.innerHTML = `
        <i class="fa-solid fa-plus"></i>
        <span>New Chat</span>
    `;

    button.title =
        "Start a new chat";

    button.setAttribute(
        "aria-label",
        "Start a new chat"
    );

    button.style.display =
        "flex";

    button.style.alignItems =
        "center";

    button.style.justifyContent =
        "center";

    button.style.gap =
        "8px";

    button.style.width =
        "100%";

    button.style.padding =
        "10px 14px";

    button.style.marginBottom =
        "12px";

    button.style.border =
        "1px solid rgba(128, 128, 128, 0.25)";

    button.style.borderRadius =
        "10px";

    button.style.background =
        "transparent";

    button.style.cursor =
        "pointer";

    button.style.fontSize =
        "14px";

    button.style.fontWeight =
        "600";

    if (
        chatHistory &&
        chatHistory.parentElement
    ) {

        chatHistory.parentElement.insertBefore(
            button,
            chatHistory
        );

    }

    else {

        document.body.prepend(
            button
        );
    }

    button.addEventListener(
        "click",
        createNewChat
    );

    return button;
}

async function renameChatFromFirstQuestion(
    conversationId,
    question
) {

    if (
        !conversationId
    ) {
        return;
    }

    const conversation =
        conversations.find(
            (item) =>
                item.id ===
                conversationId
        );

    if (
        conversation &&
        getConversationTitle(
            conversation
        ) !== "New Chat"
    ) {
        return;
    }

    let title =
        String(
            question || ""
        )
            .replace(
                /\s+/g,
                " "
            )
            .trim();

    if (
        !title
    ) {
        return;
    }

    if (
        title.length > 80
    ) {

        title =
            title.substring(
                0,
                80
            ).trim();

        title +=
            "...";
    }

    try {

        const data =
            await apiRequest(
                `/conversations/${encodeURIComponent(conversationId)}`,
                {
                    method: "PATCH",

                    body:
                        JSON.stringify({
                            user_id:
                                USER_ID,

                            title:
                                title
                        })
                }
            );

        if (
            data &&
            data.conversation
        ) {

            conversations =
                conversations.map(
                    (item) =>
                        item.id ===
                        conversationId
                            ? data.conversation
                            : item
                );
        }

        else {

            conversations =
                conversations.map(
                    (item) =>
                        item.id ===
                        conversationId
                            ? {
                                ...item,
                                title:
                                    title
                            }
                            : item
                );
        }

        renderConversationHistory();

        console.log(
            "Chat automatically renamed from first question:",
            title
        );

    }

    catch (error) {

        console.error(
            "Failed to automatically rename chat:",
            error
        );
    }
}

async function sendMessage() {

    const text =
        chatInput.value.trim();

    if (!text) {
        return;
    }

    if (
        isAiResponding
    ) {
        return;
    }

    const language =
        langSelector.value;

    if (
        !activeConversationId
    ) {

        try {

            const conversationData =
                await apiRequest(
                    "/conversations",
                    {
                        method: "POST",

                        body:
                            JSON.stringify({
                                user_id:
                                    USER_ID,

                                title:
                                    text.slice(
                                        0,
                                        80
                                    )
                            })
                    }
                );

            activeConversationId =
                conversationData
                    .conversation
                    .id;

            localStorage.setItem(
                ACTIVE_CONVERSATION_STORAGE_KEY,
                activeConversationId
            );

        }

        catch (error) {

            console.error(
                "Failed to create conversation:",
                error
            );

            appendMessage(
                "I couldn't create a chat session. Please try again.",
                "ai"
            );

            return;
        }
    }

    appendMessage(
        text,
        "user"
    );

    chatInput.value =
        "";

    updateButtonIcon();

    isAiResponding =
        true;

    updateButtonIcon();

    const thinkingMessage =
        createAiStatusMessage();

    const thinkingStatusController =
        startAiStatusAnimation(
            thinkingMessage
        );

    const requestStartTime =
        performance.now();

    try {

        debugSeparator(
            "BACKEND REQUEST"
        );

        console.log(
            "POST:",
            `${API_URL}/chat`
        );

        console.log(
            "Conversation ID:",
            activeConversationId
        );

        console.log(
            "Request:",
            {
                message: text,
                language: language,
                conversation_id:
                    activeConversationId,
                user_id:
                    USER_ID
            }
        );

        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            message:
                                text,

                            language:
                                language,

                            conversation_id:
                                activeConversationId,

                            user_id:
                                USER_ID
                        })
                }
            );

        console.log(
            "HTTP status:",
            response.status
        );

        if (!response.ok) {

            let errorDetails =
                "";

            try {

                errorDetails =
                    await response.text();

            }

            catch (_) {

                errorDetails =
                    "";
            }

            throw new Error(
                `Backend returned HTTP ${response.status}` +
                (
                    errorDetails
                        ? `: ${errorDetails}`
                        : ""
                )
            );
        }

        const data =
            await response.json();

        const requestDuration =
            performance.now() -
            requestStartTime;

        console.log(
            "Request duration:",
            `${Math.round(requestDuration)} ms`
        );

        debugSeparator(
            "BACKEND RESPONSE DEBUG"
        );

        console.log(
            "Response object:",
            data
        );

        if (
            data.conversation_id
        ) {

            activeConversationId =
                data.conversation_id;

            localStorage.setItem(
                ACTIVE_CONVERSATION_STORAGE_KEY,
                activeConversationId
            );
        }

        await finishAiStatusAnimation(
            thinkingMessage,
            thinkingStatusController
        );

        const answer =
            data.answer
                ? String(data.answer)
                : "";

        const evidence =
            Array.isArray(
                data.sources
            )
                ? data.sources
                : [];

        if (
            data.status ===
            "success"
        ) {

            appendMessage(
                answer ||
                    "I could not generate an answer.",
                "ai",
                evidence
            );
        }

        else {

            appendMessage(
                answer ||
                    "I could not find sufficient verified information to answer this reliably.",
                "ai",
                evidence
            );
        }

        await renameChatFromFirstQuestion(
            activeConversationId,
            text
        );

        await loadConversationHistory();

        debugSeparator(
            "FRONTEND RESPONSE DISPLAY COMPLETE"
        );

    }

    catch (error) {

        console.error(
            "eGovAssist API Error:",
            error
        );

        if (
            thinkingStatusController
        ) {

            thinkingStatusController.stop();
        }

        if (
            thinkingMessage &&
            thinkingMessage.parentNode
        ) {

            thinkingMessage.remove();
        }

        appendMessage(
            "I couldn't connect to the eGovAssist backend. " +
            "Please make sure the FastAPI server is running.",
            "ai"
        );
    }

    finally {

        isAiResponding =
            false;

        updateButtonIcon();

        chatInput.focus();
    }
}

actionBtn.addEventListener(
    "click",
    () => {

        if (
            isAiResponding
        ) {
            return;
        }

        if (
            chatInput.value.trim() !== ""
        ) {

            sendMessage();
        }

        else {

            alert(
                "Voice recognition will be connected later."
            );
        }
    }
);

chatInput.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.isComposing &&
            !isAiResponding
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);

langSelector.addEventListener(
    "change",
    (event) => {

        console.log(
            "Language switched to:",
            event.target.value
        );
    }
);

function initializeApplication() {

    debugSeparator(
        "eGovAssist FRONTEND STARTUP"
    );

    if (
        !validateDom()
    ) {

        console.error(
            "eGovAssist frontend failed to initialize."
        );

        return;
    }

    updateThemeIcon();

    updateButtonIcon();

    ensureNewChatButton();

    console.log(
        "Frontend initialized successfully."
    );

    console.log(
        "API:",
        API_URL
    );

    console.log(
        "User ID:",
        USER_ID
    );

    console.log(
        "Active conversation:",
        activeConversationId
    );

    console.log(
        "Marked loaded:",
        typeof marked !==
            "undefined"
    );

    console.log(
        "DOMPurify loaded:",
        typeof DOMPurify !==
            "undefined"
    );

    console.log(
        "AI processing stages:",
        AI_PROCESS_STAGES.map(
            stage =>
                stage.text
        )
    );

    loadConversationHistory();

    debugSeparator(
        "eGovAssist FRONTEND READY"
    );
}

initializeApplication();
