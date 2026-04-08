/**
 * base.home.js
 */

document.addEventListener("DOMContentLoaded", () => {

    document.fonts.load('21px "Material Symbols Rounded"').then(() => {
        document.documentElement.classList.add('fonts-loaded');
    });

    // Helper functions
    function safeAddListener(element, event, handler) {
        if (element) element.addEventListener(event, handler);
    }

    function applyRoleBasedVisibility(role) {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = (role === 'admin' || role === 'superadmin') ? '' : 'none';
        });

        document.querySelectorAll('.superadmin-only').forEach(el => {
            el.style.display = (role === 'superadmin') ? '' : 'none';
        });
    }

    applyRoleBasedVisibility(CURRENT_USERROLE);

    /**
     * Theme toggling: Switches between light and dark themes by toggling a data attribute on the root element.
     */
    const toggleBtn = document.getElementById("themeToggle");
    const root = document.documentElement;

    function toggleTheme() {
        const currentTheme = root.getAttribute("data-theme");
        const icon = toggleBtn.querySelector(".material-icons");
        if (currentTheme === "dark") {
            root.removeAttribute("data-theme");
            icon.textContent = "light_mode";
        } else {
            root.setAttribute("data-theme", "dark");
            icon.textContent = "dark_mode";
        }
         document.dispatchEvent(
            new CustomEvent("themeChanged", {
                detail: {
                    theme: currentTheme || "light"
                }
            })
        );
        fetch("/api/user/update_theme", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: CURRENT_USERNAME,
                theme: (currentTheme === "dark") ? "light" : "dark"
            })
        });
    }

    safeAddListener(toggleBtn, "click", () => {
        toggleTheme();
    });

    /**
     * User account menu: Toggles the visibility of the user account dropdown menu and handles clicks outside to close it.
     */
    const userButton = document.getElementById('userMenuToggle');
    const userMenu = document.getElementById('userPopupMenu');

    safeAddListener(userButton, 'click', (e) => {
      e.stopPropagation();
      userMenu.style.display = userMenu.style.display === 'block' ? 'none' : 'block';
    });
    window.addEventListener('click', () => {
      userMenu.style.display = 'none';
    });
    safeAddListener(userMenu, 'click', (e) => {
      e.stopPropagation();
    });

    /**
    * Password visibility toggle: Toggles the input type between 'password' and 'text' for password fields,
    * and updates the icon accordingly.
    */
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.toggle-password');
        if (!btn) return;

        const targetInput = document.querySelector(btn.getAttribute('data-target'));
        if (!targetInput) return;

        if (targetInput.type === 'password') {
            targetInput.type = 'text';
            btn.querySelector('.material-icons').textContent = 'visibility_off';
        } else {
            targetInput.type = 'password';
            btn.querySelector('.material-icons').textContent = 'visibility';
        }
    });

    /**
    * Modal section switching: Handles the logic for switching between different sections of the user account modal
    * when the corresponding menu items are clicked, and updates the content title accordingly.
    */
    const menuItems = document.querySelectorAll('.app-modal-menu .menu-item');
    const sections = document.querySelectorAll('.app-modal-section');
    const contentTitle = document.querySelectorAll('.app-modal-section-title');

    menuItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active class from all menu items and sections
            menuItems.forEach(i => i.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class to clicked menu item
            item.classList.add('active');

            // Show corresponding section
            const sectionId = item.getAttribute('data-id') + 'Section';
            document.getElementById(sectionId).classList.add('active');

            // Update content title
            const title = item.getAttribute('data-title');
            contentTitle.forEach(t => t.textContent = title);
        });
    });

    /**
    * Administration modal: Handles opening and closing of the administration modal
    * when the corresponding menu item is clicked.
    */
    const administration = document.getElementById('administration');
    const adminModal = document.getElementById('adminModal');
    const closeAdminModal = document.getElementById('closeAdminModal');

    safeAddListener(closeAdminModal, 'click', () => {
      adminModal.style.display = 'none';
    });

    safeAddListener(administration, 'click', () => {
      adminModal.style.display = 'flex';
      const firstMenuItem = adminModal.querySelector('.app-modal-menu .menu-item');
      if (firstMenuItem) firstMenuItem.click();
    });

    /**
    * Application management: Initializes the DataTable for application management, loads data via AJAX,
    * and handles add and delete operations for applications.
    */
    let applicationTable = null;

    function initApplicationTable() {
        if (applicationTable) return;
        applicationTable = $('#applicationTable').DataTable({
            searching: false,
            paging: false,
            info: false,
            responsive: true,
            scrollY: "60vh",
            scrollCollapse: true,
            ajax: {
                url: '/api/blueprints',
                dataSrc: function (resp) {
                    return Object.values(resp).map(app => ({
                        id: app.id,
                        name: app.name,
                        version: app.version,
                        description: app.description || '',
                        url_prefix: app.url_prefix || ''
                    }));
                }
            },
            columns: [
                { data: null,
                    render: function (data, type, row) {
                        const iconUrl = `/api/blueprint_icon/${row.id}`;
                        return `
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <img src="${iconUrl}" alt="${row.name} icon" style="max-width: 24px;" onerror="this.outerHTML='<span class=&quot;material-icons&quot; style=&quot;font-size:24px;&quot;>grid_view</span>'">
                                <span>${row.name}</span>
                            </div>
                        `;
                    }
                },
                { data: 'version' },
                { data: 'description' },
                {
                    data: null,
                    orderable: false,
                    render: function (data, type, row) {
                        return `
                            <div class="superadmin-only" style="display: flex; gap: 10px; justify-content: center;">
                               <button class="delete-app icon-text" data-id="${row.id}" data-name="${row.name}">
                                   <span class="material-icons">delete</span>
                                   <span>Delete</span>
                               </button>
                            </div>
                        `;
                    }
                }
            ]
        });
    }

     // Initialize application table when administration modal is opened
     $('.app-modal-menu .menu-item[data-id="applications"]').on('click', () => {
        initApplicationTable();
        applicationTable.ajax.reload(null, false);
    });

    $('#addApplication').on('click', function () {
        $('#appModalForm')[0].reset();
        $("#appModalOverlay").css("display", "flex");
    });

    $('#appCloseModalBtn').on('click', function () {
        $("#appModalOverlay").css("display", "none");
    });


    $('#uploadAppBtn').on('click', function () {
        const dirInput = $('<input type="file" webkitdirectory directory multiple style="display:none;">');

        dirInput.on('change', function (event) {
            const files = event.target.files;

            if (!files.length) return;

            const rootDir = files[0].webkitRelativePath.split('/')[0];
            $('#appDir').val(rootDir);

            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file, file.webkitRelativePath);
            }

            $.ajax({
                url: '/api/blueprint/upload',
                method: 'POST',
                data: formData,
                processData: false,
                contentType: false,

                beforeSend: function () {
                    $('#uploadAppBtn')
                        .prop('disabled', true)
                        .html(`
                            <span class="material-icons">hourglass_top</span>
                            Uploading...
                        `);
                },

                success: function () {
                    clearBlueprintCache();

                    if (applicationTable) {
                        applicationTable.ajax.reload(null, false);
                    }

                    $('#appModalOverlay').hide();

                    $('#appDir').val('');
                },

                error: function (err) {
                    alert(err.responseJSON?.error || 'Upload failed');
                },
                complete: function () {
                    $('#uploadAppBtn')
                        .prop('disabled', false)
                        .html(`
                            <span class="material-icons">upload</span>
                            Upload
                        `);
                }
            });
        });
        dirInput.trigger('click');
    });

    $(document).on('click', '.delete-app', function () {
        const appId = $(this).data('id');
        const appName = $(this).data('name');

        const confirmed = confirm(`Delete application "${appName}"?`);

        if (!confirmed) return;

        $.ajax({
            url: '/api/blueprint/delete',
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({
                keys: [appId]
            }),

            beforeSend: () => {
                $(this)
                    .prop('disabled', true)
                    .html(`
                        <span class="material-icons">hourglass_top</span>
                        Deleting...
                    `);
            },

            success: function () {
                // clear dropdown cache
                clearBlueprintCache();

                // refresh DataTable
                if (applicationTable) {
                    applicationTable.ajax.reload(null, false);
                }
            },

            error: function (err) {
                alert(err.responseJSON?.error || 'Delete failed');
            }
        });
    });

    /**
    * User management: Initializes the DataTable for user management, loads data via AJAX,
    * and handles add, edit, and delete operations for users.
    */
    let userTable = null;

    function initUserTable() {
        if (userTable) return;
        userTable = $('#userTable').DataTable({
            searching: false,
            paging: false,
            info: false,
            responsive: true,
            scrollY: "60vh",
            scrollCollapse: true,
            ajax: {
                url: '/api/users',
                dataSrc: function (resp) {
                    if (!resp.success || !resp.users) return [];
                    return Object.entries(resp.users).map(([username, data]) => ({
                        username: username,
                        display_name: `${data.profile.firstname} ${data.profile.lastname}`,
                        role: data.meta.role,
                        email: data.profile.email,
                        last_login: data.meta.last_login
                    }));
                }
            },
            columns: [
                { data: 'username' },
                { data: 'display_name' },
                { data: 'role' },
                { data: 'email' },
                {
                    data: 'last_login',
                    render: function (data) {
                        if (!data) return 'Never';
                        return new Date(data).toLocaleDateString('en-GB', {
                            day: '2-digit',
                            month: 'short',
                            year: 'numeric'
                        }).replace(/ /g, '-');
                    }
                },
                {
                    data: null,
                    orderable: false,
                    render: () => `
                     <div class="superadmin-only" style="display: flex; gap: 10px; justify-content: center;">
                        <button class="change-role icon-text">
                            <span class="material-icons">person_edit</span>
                            <span>Change Role</span>
                        </button>
                        ${AUTH_MODE === 'local' ? `
                        <button class="delete-user icon-text">
                            <span class="material-icons">delete</span>
                            <span>Delete</span>
                        </button>
                         ` : ''}
                     </div>`
                }
            ],
            drawCallback: function () {
                document.querySelectorAll('.change-role, .delete-user').forEach(button => {
                    button.style.display = (CURRENT_USERROLE === 'superadmin') ? '' : 'none';
                });
            }
        });
    }

    // Add user modal
    const addUser = document.getElementById('addUser');
    const addUserModalOverlay = document.getElementById('addUserModalOverlay');
    const closeAddUserModal = document.getElementById('closeAddUserModal');

    safeAddListener(addUser, 'click', () => {
        $('#addUserForm')[0].reset();
        addUserModalOverlay.style.display = 'flex';
    });

    safeAddListener(closeAddUserModal, 'click', () => {
        addUserModalOverlay.style.display = 'none';
    });

     // Initialize user table when administration modal is opened
     $('.app-modal-menu .menu-item[data-id="users"]').on('click', () => {
        initUserTable();
        userTable.ajax.reload(null, false);
    });

    // Add user
    $('#addUserForm').on('submit', function (e) {
        e.preventDefault();
        const formData = {
            username: $('#newUsername').val().trim(),
            password: $('#newPassword').val(),
            role: $('input[name="role"]:checked').val(),
            email: $('#newEmail').val().trim(),
            firstname: $('#newFirstName').val().trim(),
            lastname: $('#newLastName').val().trim()
        };

        $.ajax({
            url: '/api/user/add',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'User creation failed');
                    return;
                }
                $('#addUserModalOverlay').hide();
                userTable.ajax.reload(null, false);
            },
            error: function () {
                alert('User creation failed');
            }
        });
    });

    // Change user role modal
    $('#userTable').on('click', '.change-role', function () {
        const row = userTable.row($(this).closest('tr')).data();
        $('#changeRoleUsername').val(row.username);
        $('#currentRoleUser').val(row.role);
        $('#changeUserRoleModalOverlay').css('display', 'flex');
    });

    $('#closeChangeUserRoleModal').on('click', function () {
        $('#changeUserRoleModalOverlay').css('display', 'none');
    });

    $('#changeUserRoleForm').on('submit', function (e) {
        e.preventDefault();
        const username = $('#changeRoleUsername').val();
        const newRole = $('input[name="new_role"]:checked').val();

        $.ajax({
            url: '/api/user/change_role',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username, role: newRole }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Role change failed');
                    return;
                }
                $('#changeUserRoleModalOverlay').hide();
                userTable.ajax.reload(null, false);
            },
            error: function () {
                alert('Role change failed');
            }
        });
    });

     // Delete user entry
     $('#userTable').on('click', '.delete-user', function () {
        const row = userTable.row($(this).closest('tr')).data();

        if (!confirm(`Delete user "${row.username}"?`)) return;

        $.ajax({
            url: '/api/user',
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({ username: row.username }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Delete failed');
                    return;
                }
                userTable.ajax.reload(null, false);
            },
            error: function () {
                alert('Delete failed');
            }
        });
    });

    /**
    * User account modal: Handles opening and closing of the user account modal
    * when the corresponding menu item is clicked.
    */
    const userAccount = document.getElementById('userAccount');
    const userAccountModal = document.getElementById('userAccountModal');
    const closeUserAccountModal = document.getElementById('closeUserAccountModal');

    safeAddListener(closeUserAccountModal, 'click', () => {
      userAccountModal.style.display = 'none';
    });

    safeAddListener(userAccount, 'click', () => {
      userAccountModal.style.display = 'flex';
      const firstMenuItem = userAccountModal.querySelector('.app-modal-menu .menu-item');
      if (firstMenuItem) firstMenuItem.click();
    });

    /**
    * User profile update: Handles the submission of the user profile form via AJAX,
    * updates the profile on the server, and reloads the page on success.
    */
    $("#generalForm").on("submit", function (e) {
        e.preventDefault()
        $.ajax({
            url: "/api/update_profile",
            method: "POST",
            data: $(this).serialize(),
            success: function (response) {
                $("#userAccountModal").fadeOut(150)
                location.reload()
            },
            error: function () {
                alert("Error updating profile. Please try again.");
            },
        });
    });

    /**
    * User connectors management: Initializes the DataTable for user connectors, loads data via AJAX,
    * and handles opening of the add connector modal.
    */
    let userConnectorTable = null;

    function initUserConnectorTable() {
        if (userConnectorTable) return;
        userConnectorTable = $('#userConnectorTable').DataTable({
            searching: false,
            paging: false,
            info: false,
            autoWidth: true,
            responsive: true,
            scrollY: "60vh",
            scrollCollapse: true,
            ajax: {
                url: '/api/connectors',
                dataSrc: function (resp) {
                    if (!resp.success || !resp.connectors) return [];
                    return Object.entries(resp.connectors).map(([name, data]) => ({
                        name: name,
                        jumphost_ip: data.jumphost_ip || '',
                        jumphost_username: data.jumphost_username || '',
                        network_username: data.network_username || ''
                    }));
                }
            },
            columns: [
                { data: 'name' },
                { data: 'jumphost_ip' },
                { data: 'jumphost_username' },
                { data: 'network_username' },
                {
                    data: null,
                    orderable: false,
                    render: () => `
                     <div style="display: flex; gap: 10px; justify-content: center;">
                        <button class="edit-user-connector icon-text">
                            <span class="material-icons">edit_square</span>
                            <span>Edit</span>
                        </button>
                        <button class="delete-user-connector icon-text">
                            <span class="material-icons">delete</span>
                            <span>Delete</span>
                        </button>
                     </div>`
                }
            ]
        });
    }

    // Initialize connectors table when user account modal is opened
    $('.app-modal-menu .menu-item[data-id="connectors"]').on('click', () => {
        initUserConnectorTable();
        userConnectorTable.ajax.reload(null, false);
    });

    // Add connector modal
    const addConnector = document.getElementById('addConnector');
    const userConnectorModalOverlay = document.getElementById('userConnectorModalOverlay');
    const closeUserConnectorModal = document.getElementById('closeUserConnectorModal');

    safeAddListener(addConnector, 'click', () => {
        $('#userConnectorForm')[0].reset();
        $('#userConnectorName').prop('disabled', false);
        $('#userConnectorModalTitle').text('Add Connector');
        userConnectorModalOverlay.style.display = 'flex';
    });

    safeAddListener(closeUserConnectorModal, 'click', () => {
        userConnectorModalOverlay.style.display = 'none';
    });

    // Edit connector modal
    $('#userConnectorTable').on('click', '.edit-user-connector', function () {
        const row = userConnectorTable.row($(this).closest('tr')).data();

        $.getJSON('/api/connectors', function (resp) {
            if (!resp.success) return;

            const connector = resp.connectors[row.name];
            if (!connector) return;

            $('#userConnectorName').val(row.name).prop('disabled', true);
            $('#userConnectorJumphostIp').val(connector.jumphost_ip || '');
            $('#userConnectorJumphostUsername').val(connector.jumphost_username || '');
            $('#userConnectorJumphostPassword').val(connector.jumphost_password || '');
            $('#userConnectorNetUsername').val(connector.network_username || '');
            $('#userConnectorNetPassword').val(connector.network_password || '');
            $('#userConnectorModalTitle').text('Edit Connector');
            $('#userConnectorModalOverlay').css('display', 'flex');
        });
    });

    // Save connector (both add and edit)
    $('#userConnectorForm').on('submit', function (e) {
        e.preventDefault();

        const name = $('#userConnectorName').val().trim();
        if (!name) return;

        const data = {
            jumphost_ip: $('#userConnectorJumphostIp').val(),
            jumphost_username: $('#userConnectorJumphostUsername').val(),
            jumphost_password: $('#userConnectorJumphostPassword').val(),
            network_username: $('#userConnectorNetUsername').val(),
            network_password: $('#userConnectorNetPassword').val()
        };

        $.ajax({
            url: '/api/connector',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ name, data }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Save failed');
                    return;
                }
                $('#userConnectorModalOverlay').hide();
                userConnectorTable.ajax.reload(null, false);
            },
            error: function () {
                alert('Save failed');
            }
        });
    });

    // Delete connector entry
    $('#userConnectorTable').on('click', '.delete-user-connector', function () {
        const row = userConnectorTable.row($(this).closest('tr')).data();

        if (!confirm(`Delete Connector entry "${row.name}"?`)) return;

        $.ajax({
            url: '/api/connector',
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({ name: row.name }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Delete failed');
                    return;
                }
                userConnectorTable.ajax.reload(null, false);
            },
            error: function () {
                alert('Delete failed');
            }
        });
    });

    /**
     * Application dropdown:
     * Fetches applications (blueprints), populates dropdown,
     * restores selected app based on current URL,
     * handles navigation, loading, and error states.
     */
    const applicationDropdownToggle = document.getElementById("applicationDropdownToggle");
    const applicationDropdownMenu = document.getElementById("applicationDropdownMenu");

    // Toggle dropdown open/close
    safeAddListener(applicationDropdownToggle, "click", () => {
        applicationDropdownMenu.classList.toggle("show");
    });

    // Initial loading state
    applicationDropdownToggle.innerHTML = `
        Loading applications...
    `;

    const BLUEPRINT_CACHE_KEY = "cached_blueprints";
    const BLUEPRINT_CACHE_TIME_KEY = "cached_blueprints_time";
    const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

    function getCachedBlueprints() {
        const cached = localStorage.getItem(BLUEPRINT_CACHE_KEY);
        const cachedTime = localStorage.getItem(BLUEPRINT_CACHE_TIME_KEY);

        if (!cached || !cachedTime) return null;

        const isExpired = Date.now() - Number(cachedTime) > CACHE_TTL;

        if (isExpired) {
            clearBlueprintCache();
            return null;
        }

        return JSON.parse(cached);
    }

    function setBlueprintCache(data) {
        localStorage.setItem(BLUEPRINT_CACHE_KEY, JSON.stringify(data));
        localStorage.setItem(BLUEPRINT_CACHE_TIME_KEY, Date.now());
    }

    function clearBlueprintCache() {
        localStorage.removeItem(BLUEPRINT_CACHE_KEY);
        localStorage.removeItem(BLUEPRINT_CACHE_TIME_KEY);
    }

    function loadBlueprintData() {
        const cachedData = getCachedBlueprints();

        if (cachedData) {
            return Promise.resolve(cachedData);
        }

        return fetch("/api/blueprints")
            .then(response => response.json())
            .then(data => {
                setBlueprintCache(data);
                return data;
            });
    }

    // Fetch applications
    loadBlueprintData()
        .then(data => {
            const apps = Object.values(data);

            // No apps available
            if (!apps.length) {
                applicationDropdownToggle.innerHTML = `
                    No app available
                `;
                return;
            }

            // Get current app from URL path
            currentAppUrl = `/${window.location.pathname.split("/")[1]}`;

            // Find selected app from URL, fallback to first app
            const selectedApp = apps.find(app => app.url_prefix === currentAppUrl) || apps[0];

            // Redirect from home page to first available app
            if (window.location.pathname === "/home") {
                window.location.href = `${apps[0].url_prefix}`;
                return;
            }

            // Set selected app in toggle button
            applicationDropdownToggle.innerHTML = `
                <img src="/api/blueprint_icon/${selectedApp.id}"
                     class="application-dropdown-icon"
                     style="margin-right:8px;"
                     onerror="this.outerHTML='<span class=&quot;material-icons application-dropdown-icon&quot; style=&quot;margin-right:8px;font-size:24px;&quot;>grid_view</span>'">
                ${selectedApp.name}
            `;

            // Clear dropdown before populating
            applicationDropdownMenu.innerHTML = "";

            // Populate dropdown menu
            apps.forEach(app => {
                const item = document.createElement("div");
                item.className = "application-dropdown-item";

                // Highlight selected app
                if (app.id === selectedApp.id) {
                    item.classList.add("active");
                }

                item.innerHTML = `
                    <img src="/api/blueprint_icon/${app.id}"
                         class="application-dropdown-icon"
                         onerror="this.outerHTML='<span class=&quot;material-icons application-dropdown-icon&quot; style=&quot;margin-right:8px;font-size:24px;&quot;>grid_view</span>'">
                    <div class="application-dropdown-text">
                        <div class="application-dropdown-name">${app.name}</div>
                        <div class="application-dropdown-description">
                            ${app.description || ""}
                        </div>
                    </div>
                `;

                // Navigate on click
                item.addEventListener("click", () => {
                    // Update button immediately for better UX
                    applicationDropdownToggle.innerHTML = `
                        <img src="/api/blueprint_icon/${app.id}"
                             class="application-dropdown-icon"
                             style="margin-right:8px;"
                             onerror="this.outerHTML='<span class=&quot;material-icons application-dropdown-icon&quot; style=&quot;margin-right:8px;font-size:24px;&quot;>grid_view</span>'">
                        ${app.name}
                    `;

                    // Close dropdown
                    applicationDropdownMenu.classList.remove("show");

                    // Navigate
                    window.location.href = `${app.url_prefix}`;
                });

                applicationDropdownMenu.appendChild(item);
            });
        })
        .catch(error => {
            console.error("Error loading blueprints:", error);

            applicationDropdownToggle.innerHTML = `
                <span class=&quot;material-icons application-dropdown-icon&quot; style=&quot;margin-right:8px;font-size:24px;&quot;>apps_outage</span>
                Failed to load apps
            `;
        });

    // Close dropdown when clicking outside
    window.addEventListener("click", (e) => {
        if (
            !applicationDropdownToggle.contains(e.target) &&
            !applicationDropdownMenu.contains(e.target)
        ) {
            applicationDropdownMenu.classList.remove("show");
        }
    });


    /**
     * Sidebar toggle:
     * Handles collapse/expand state and saves to localStorage
     */
    const mainLayout = document.getElementById("mainLayout");
    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (sidebar && sidebarToggle) {
        const icon = sidebarToggle.querySelector(".material-icons");
        const SIDEBAR_STATE = "atx_sidebar_collapsed";

        // Restore saved state
        const savedState = localStorage.getItem(SIDEBAR_STATE);
        const isCollapsed = savedState === "true";

        sidebar.classList.toggle("collapsed", isCollapsed);
        mainLayout.classList.toggle("sidebar-collapsed", isCollapsed);
        mainLayout.classList.toggle("sidebar-expanded", !isCollapsed);

        icon.textContent = isCollapsed
            ? "chevron_right"
            : "chevron_left";

        // Toggle sidebar
        sidebarToggle.addEventListener("click", () => {
            const collapsed = sidebar.classList.toggle("collapsed");

            mainLayout.classList.toggle("sidebar-collapsed", collapsed);
            mainLayout.classList.toggle("sidebar-expanded", !collapsed);

            icon.textContent = collapsed
                ? "chevron_right"
                : "chevron_left";

            localStorage.setItem(SIDEBAR_STATE, collapsed);
        });
    }


    /**
     * Menu navigation:
     * Handles click navigation and active state
     */
    document.querySelectorAll(".menu-item[data-href]").forEach(item => {
        item.addEventListener("click", () => {
            window.location.href = item.dataset.href;
        });

        const href = item.dataset.href;
        if (window.location.pathname === href) {
            item.classList.add("active");
        }
    });

});