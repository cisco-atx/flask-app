/**
 * atx.utils.js
 *
 * This file contains utility functions for the ATX application, including:
 * 1. RunModal: A modal dialog for selecting a connector at runtime.
 * 2. ensureDeviceConnectors: A function that builds a device-to-connector map, prompting the user if any device lacks a connector.
 * These utilities help manage connectors and device configurations within the ATX application.
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


