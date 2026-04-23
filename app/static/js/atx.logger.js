/**
 * atx.logger.js
 *
 * This script implements a real-time logging dock for a Flask web application.
 * Main functionalities include:
 * - Establishing a Server-Sent Events (SSE) connection to receive log updates.
 * - Rendering log entries in a table format with filtering options by log level.
 * - Allowing users to toggle the visibility of the logger dock and persist their preferences using localStorage.
 * - Providing auto-scrolling to the latest log entries and visual indicators for different log levels.
 *
 * This enhances the developer experience by providing immediate feedback on application events and errors directly within the web interface.
 */


let loggerEventSource;

$(document).ready(function () {
    initLogger();
});

/**
 * Initializes the logger dock and its associated functionality.
 */
function initLogger() {
    const loggerOutput = document.querySelector('#loggerTable tbody');
    const loggerToggle = document.getElementById("loggerToggle");
    const loggerDock = document.getElementById("loggerDock");
    const levelCheckboxes = document.querySelectorAll('.logger-filters .filter');

    if (!loggerOutput) return;

    restoreDockState();
    restoreSelectedLogLevels();
    setupDockToggle();
    setupLogLevelCheckboxes();
    startSSE();

    /**
     * Restores the dock visibility state from localStorage.
     */
    function restoreDockState() {
        const savedDockState = localStorage.getItem("loggerDockOpen");
        if (savedDockState === "true") {
            loggerDock.classList.add("open");
            loggerToggle.innerHTML = '<span class="material-icons">keyboard_arrow_down</span><span>Logger</span>';
        } else {
            loggerDock.classList.remove("open");
            loggerToggle.innerHTML = '<span class="material-icons">keyboard_arrow_up</span><span>Logger</span>';
        }
    }

    /**
     * Restores the selected log levels filter state from localStorage.
     */
    function restoreSelectedLogLevels() {
        const savedLevels = JSON.parse(localStorage.getItem("loggerSelectedLevels") || '[]');
        if (savedLevels.length) {
            levelCheckboxes.forEach(cb => {
                cb.checked = savedLevels.includes(cb.value);
            });
        }
    }


    /**
        * Starts a Server-Sent Events (SSE) connection to receive real-time log updates.
    */
    function startSSE() {
        if (loggerEventSource) {
            loggerEventSource.close();
        }

        loggerEventSource = new EventSource('/activity');

        loggerEventSource.onmessage = updateUi;

        loggerEventSource.onerror = () => {
            console.warn("Logger stream disconnected");
            loggerEventSource.close();

            setTimeout(() => {
                startSSE();
            }, 3000);
        };
    }

    /**
     * Updates the UI with new log entries received from the SSE connection.
     * It checks if the log level matches the selected filters before rendering.
     * @param {MessageEvent} event - The event containing the log data.
     */
    function updateUi(event) {
        const log = JSON.parse(event.data);
        const selectedLevels = getSelectedLevels();
        if (selectedLevels.includes(log.levelname)) {
            renderLogRow(log);
            autoScrollToBottom();
        }
    }

    /**
     * Retrieves the currently selected log levels.
     * @returns {Array} - An array of selected log levels.
     */
    function getSelectedLevels() {
        return Array.from(levelCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
    }

    /**
     * Renders an individual log entry as a table row.
     * @param {Object} log - The log entry to render.
     */
    function renderLogRow(log) {
        const row = document.createElement('tr');
        row.dataset.level = log.levelname;
        const iconName =
            log.levelname === 'ERROR' ? 'error' :
            log.levelname === 'WARNING' ? 'warning' :
            log.levelname === 'INFO' ? 'info' :
            log.levelname === 'CRITICAL' ? 'dangerous' :
            log.levelname === 'DEBUG' ? 'bug_report' : '';

        row.innerHTML = `
            <td class="timestamp">${log.asctime}</td>
            <td>
                <span class="badge ${log.levelname.toLowerCase()}">
                    <span class="material-icons badge-icon">${iconName}</span>
                    <span>${log.levelname}</span>
                </span>
            </td>
            <td class="module">${log.module || ''}</td>
            <td class="message">${log.message}</td>
        `;

        loggerOutput.appendChild(row);
    }

    /**
     * Auto-scrolls the logger table to the bottom.
     */
    function autoScrollToBottom() {
        const wrapper = loggerDock.querySelector('.logger-table');
        wrapper.scrollTop = wrapper.scrollHeight;
    }

    /**
     * Sets up the event listener for toggling the dock visibility.
     */
    function setupDockToggle() {
        loggerToggle.addEventListener("click", () => {
            loggerDock.classList.toggle("open");
            const isOpen = loggerDock.classList.contains("open");
            localStorage.setItem("loggerDockOpen", isOpen);
            loggerToggle.innerHTML = isOpen
                ? '<span class="material-icons">keyboard_arrow_down</span><span>Logger</span>'
                : '<span class="material-icons">keyboard_arrow_up</span><span>Logger</span>';
        });
    }

    /**
     * Sets up event listeners for log level checkboxes.
     * Updates the selected log levels in localStorage and fetches logs on change.
     */
    function setupLogLevelCheckboxes() {
        levelCheckboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                localStorage.setItem("loggerSelectedLevels", JSON.stringify(getSelectedLevels()));
                applyFilters();
            });
        });
    }


    /**
    * Apply filters to existing log rows based on selected log levels.
    */
    function applyFilters() {
        const selectedLevels = getSelectedLevels();
        const rows = loggerOutput.querySelectorAll('tr');
        rows.forEach(row => {
            const level = row.dataset.level;
            row.style.display = selectedLevels.includes(level) ? '' : 'none';
        });
    }
}