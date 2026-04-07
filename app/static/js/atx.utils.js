/**
 * Generic Run Modal
 * - Opens modal
 * - Loads connectors
 * - Returns selected connector config
 */

document.addEventListener("DOMContentLoaded", () => {
    window.RunModal = (() => {

        let onConfirmCallback = null;

        const modal = document.getElementById("runModal");
        const form = document.getElementById("runModalForm");
        const connectorSelect = document.getElementById("runModalConnectors");

        async function loadConnectors() {
            connectorSelect.innerHTML =
                `<option value="">-- Select Connector --</option>`;

            const res = await fetch("/api/connectors");
            if (!res.ok) throw new Error("Failed to load connectors");

            const data = await res.json();
            if (!data.success || !data.connectors) return;

            Object.entries(data.connectors).forEach(([name]) => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.textContent = name;
                connectorSelect.appendChild(opt);
            });
        }

        async function open(onConfirm) {
            onConfirmCallback = onConfirm;
            await loadConnectors();
            modal.style.display = "flex";
        }

        function close() {
            modal.style.display = "none";
            form.reset();
        }

        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const connectorName = connectorSelect.value;
            if (!connectorName) return alert("Please select a connector");

            const res = await fetch("/api/connectors");
            const data = await res.json();

            const connectorConfig = data.connectors?.[connectorName];
            if (!connectorConfig) {
                alert("Connector not found");
                return;
            }

            close();

            if (typeof onConfirmCallback === "function") {
                onConfirmCallback({
                    name: connectorName,
                    config: connectorConfig
                });
            }
        });

        document.getElementById("closeRunModal").onclick = close;

        modal.addEventListener("click", e => {
            if (e.target === modal) close();
        });

        return { open };
    })();
});


/**
 * Builds a device → full connector config map.
 * Prompts user if any device lacks a connector.
 */
window.ensureDeviceConnectors = async function (deviceIds) {

    // Load device store
    const devRes = await fetch("/netaudit/api/devices");
    if (!devRes.ok) throw new Error("Failed to load devices");
    const devices = await devRes.json();

    // Load connector store
    const connRes = await fetch("/netaudit/api/connectors");
    if (!connRes.ok) throw new Error("Failed to load connectors");
    const connectors = await connRes.json();

    const deviceConnectorMap = {};
    const missing = [];

    deviceIds.forEach(deviceId => {
        const connectorId = devices[deviceId]?.connector ?? null;

        if (connectorId) {
            const connectorConfig = connectors[connectorId];
            if (!connectorConfig) {
                throw new Error(`Connector '${connectorId}' not found`);
            }
            deviceConnectorMap[deviceId] = connectorConfig;
        } else {
            deviceConnectorMap[deviceId] = null;
            missing.push(deviceId);
        }
    });

    // All devices resolved
    if (!missing.length) {
        return deviceConnectorMap;
    }

    // Ask user for runtime connector
    return new Promise((resolve) => {
        RunModal.open(({ config }) => {
            missing.forEach(deviceId => {
                deviceConnectorMap[deviceId] = config;
            });
            resolve(deviceConnectorMap);
        });
    });
};


