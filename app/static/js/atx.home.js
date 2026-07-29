/**
 * atx.home.js
 *
 * This JavaScript file manages the main functionalities of the home page, including:
 * - Theme toggling between light and dark modes, with persistence via server update.
 * - Role-based visibility of UI elements for admin and superadmin users.
 * - User account menu handling, including profile updates and connector management.
 * - Administration modal for managing applications and users, with DataTable integration.
 * - Application dropdown for navigating between registered applications, with caching for performance.
 * The code ensures a responsive and interactive user experience while maintaining security and access control based on user roles.
 */


document.addEventListener("DOMContentLoaded", () => {

    // Load Material Symbols Rounded font and add class to root element when loaded for better font loading control
    document.fonts.load('21px "Material Symbols Rounded"').then(() => {
        document.documentElement.classList.add('fonts-loaded');
    });

    // Helper functions
    function safeAddListener(element, event, handler) {
        if (element) element.addEventListener(event, handler);
    }

    // Role-based visibility: Shows or hides elements based on the current user's role by toggling their display style.
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
     * Notification / Announcement banner:
     * Renders dismissible banners fed by /api/notifications. Dismissed IDs
     * persist in localStorage (unless the notification is persistent) so
     * they don't reappear on reload. Type drives styling via badge tokens.
     */
    const notificationBar = document.getElementById("notificationBar");
    const DISMISSED_NOTIFICATIONS_KEY = "dismissed_notifications";

    const NOTIFICATION_ICONS = {
        info: "info",
        warning: "warning",
        maintenance: "build",
        critical: "error"
    };

    function getDismissedNotifications() {
        try {
            return JSON.parse(localStorage.getItem(DISMISSED_NOTIFICATIONS_KEY)) || [];
        } catch {
            return [];
        }
    }

    function dismissNotification(id) {
        const dismissed = getDismissedNotifications();
        if (!dismissed.includes(id)) {
            dismissed.push(id);
            localStorage.setItem(
                DISMISSED_NOTIFICATIONS_KEY,
                JSON.stringify(dismissed)
            );
        }
    }

    function renderNotification(note) {
        const type = note.type || "info";
        const icon = NOTIFICATION_ICONS[type] || "info";

        const banner = document.createElement("div");
        banner.className = `notification-item notification-${type}`;
        banner.dataset.id = note.id;

        banner.innerHTML = `
            <span class="material-icons notification-icon">${icon}</span>
            <div class="notification-message">
                ${note.title ? `<strong>${note.title}</strong> ` : ""}
                <span>${note.message}</span>
            </div>
            <button class="notification-close icon-only" title="Dismiss">
                <span class="material-icons">close</span>
            </button>
        `;

        banner.querySelector(".notification-close").addEventListener("click", () => {
            if (!note.persistent) {
                dismissNotification(note.id);
            }
            banner.remove();
        });

        notificationBar.appendChild(banner);
    }

    function loadNotifications() {
        if (!notificationBar) return;

        fetch("/api/notifications")
            .then(resp => resp.json())
            .then(data => {
                if (!data.success) return;
                const notes = data.notifications || [];
                const dismissed = getDismissedNotifications();

                // Prune stale dismissed IDs no longer served by the backend.
                const activeIds = new Set(notes.map(n => n.id));
                const prunedDismissed = dismissed.filter(id => activeIds.has(id));
                if (prunedDismissed.length !== dismissed.length) {
                    localStorage.setItem(
                        DISMISSED_NOTIFICATIONS_KEY,
                        JSON.stringify(prunedDismissed)
                    );
                }

                notes
                    .filter(note => note.persistent || !prunedDismissed.includes(note.id))
                    .forEach(renderNotification);
            })
            .catch(err => console.error("Failed to load notifications:", err));
    }

    loadNotifications();

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
        if (applicationTable && !applicationTable.data().any()) {
            window.location.href = '/home';
        }
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
                        url_prefix: app.url_prefix || '',
                        git_managed: app.git_managed || false
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
                    data: 'git_managed',
                    orderable: false,
                    render: function (gitManaged, type, row) {
                        const syncButton = gitManaged
                            ? `
                                <button class="pull-app icon-text" data-id="${row.id}" data-name="${row.name}"
                                    title="Pull latest changes from Git"
                                >
                                    <span class="material-icons">sync</span>
                                    <span>Sync</span>
                                </button>`
                            : `<button class="icon-text" disabled title="Not a Git-managed blueprint">
                                    <span class="material-icons">sync_disabled</span>
                                    <span>Sync</span>
                                </button>
                            `;
                        return `<div class="superadmin-only"
                                style="
                                    display:flex;
                                    gap:10px;
                                    justify-content:center;
                                    align-items:center;
                                "
                            >
                                ${syncButton}
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

    $('#gitCloneBtn').on('click', function () {
        const repoUrl = $('#gitRepoUrl').val().trim();
        if (!repoUrl) {
            alert('Please enter a Git repository URL');
            return;
        }
        const btn = $(this);
        $.ajax({
            url: '/api/blueprint/git_clone',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                repo_url: repoUrl
            }),
            beforeSend: function () {
                btn.prop('disabled', true)
                   .html(`
                       <span class="material-icons">hourglass_top</span>
                       Cloning...
                   `);
            },
            success: function () {
                clearBlueprintCache();
                if (applicationTable) {
                    applicationTable.ajax.reload(null, false);
                }
                $('#gitRepoUrl').val('');
                $('#appModalOverlay').hide();
                alert(
                    'Blueprint cloned successfully.\n' +
                    'Reload Flask server to activate.'
                );
            },
            error: function (err) {
                alert(
                    err.responseJSON?.error ||
                    'Clone failed'
                );
            },
            complete: function () {
                btn.prop('disabled', false)
                   .html(`
                       <span class="material-icons">download</span>
                       Clone
                   `);
            }
        });
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

    $(document).on('click', '.pull-app', function () {
        const appId = $(this).data('id');
        const appName = $(this).data('name');
        const btn = $(this);
        $.ajax({
            url: '/api/blueprint/git_pull',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                blueprint_id: appId
            }),
            beforeSend: function () {
                btn.prop('disabled', true)
                   .html(`
                       <span class="material-icons">hourglass_top</span>
                       Pulling...
                   `);
            },
            success: function (resp) {
                clearBlueprintCache();
                if (applicationTable) {
                    applicationTable.ajax.reload(null, false);
                }
                alert(
                    `Updated ${appName}\n\n${resp.message}`
                );
            },
            error: function (err) {
                alert(
                    err.responseJSON?.error ||
                    'Git pull failed'
                );
            },
            complete: function () {
                btn.prop('disabled', false)
                   .html(`
                       <span class="material-icons">sync</span>
                       Pull
                   `);
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
                        <button class="edit-user icon-text">
                            <span class="material-icons">edit_square</span>
                            <span>Edit</span>
                        </button>
                        <button class="change-role icon-text">
                            <span class="material-icons">person_edit</span>
                            <span>Change Role</span>
                        </button>
                        <button class="delete-user icon-text">
                            <span class="material-icons">delete</span>
                            <span>Delete</span>
                        </button>
                     </div>`
                }
            ],
            drawCallback: function () {
                document.querySelectorAll('.edit-user, .change-role, .delete-user').forEach(button => {
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

    // Provider-aware Add User: password applies only to the local provider.
    function isLocalProvider(providerId) {
        return providerId === 'local';
    }

    // Toggle password field requirement/visibility based on provider choice.
    $('#newUserProvider').on('change', function () {
        const local = isLocalProvider($(this).val());
        $('#newPassword').prop('required', local);
        $('#newPassword').closest('label').toggle(local);
        $('#newPassword').toggle(local);
    });

    // Add user
    $('#addUserForm').on('submit', function (e) {
        e.preventDefault();
        const provider = $('#newUserProvider').val() || 'local';
        const formData = {
            username: $('#newUsername').val().trim(),
            password: isLocalProvider(provider) ? $('#newPassword').val() : null,
            role: $('input[name="role"]:checked').val(),
            email: $('#newEmail').val().trim(),
            firstname: $('#newFirstName').val().trim(),
            lastname: $('#newLastName').val().trim(),
            auth_provider: provider
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
            error: function (err) {
                alert(err.responseJSON?.message || 'User creation failed');
            }
        });
    });

    // Edit local user: open modal pre-filled, submit profile/role/password.
    const editUserModalOverlay = document.getElementById('editUserModalOverlay');

    safeAddListener(document.getElementById('closeEditUserModal'), 'click', () => {
        editUserModalOverlay.style.display = 'none';
    });

    $('#userTable').on('click', '.edit-user', function () {
        const row = userTable.row($(this).closest('tr')).data();
        $.getJSON('/api/users', function (resp) {
            const data = (resp.users || {})[row.username] || {};
            const profile = data.profile || {};
            const clean = (v) => (!v || v === 'NA') ? '' : v;

            $('#editUsername').val(row.username);
            $('#editFirstName').val(clean(profile.firstname));
            $('#editLastName').val(clean(profile.lastname));
            $('#editEmail').val(clean(profile.email));
            $('#editPassword').val('');

            // Password only meaningful for local-provider users.
            const isLocal = (data.meta || {}).auth_provider === 'local';
            $('#editPassword').closest('label').toggle(isLocal);
            $('#editPassword').toggle(isLocal);

            editUserModalOverlay.style.display = 'flex';
        });
    });

    $('#editUserForm').on('submit', function (e) {
        e.preventDefault();
        const payload = {
            username: $('#editUsername').val(),
            firstname: $('#editFirstName').val().trim(),
            lastname: $('#editLastName').val().trim(),
            email: $('#editEmail').val().trim(),
            password: $('#editPassword').val()  // blank => unchanged
        };
        $.ajax({
            url: '/api/user/update',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Update failed');
                    return;
                }
                editUserModalOverlay.style.display = 'none';
                userTable.ajax.reload(null, false);
            },
            error: function (err) {
                alert(err.responseJSON?.message || 'Update failed');
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
     * Notification management (admin):
     * DataTable listing + add/edit/delete of announcement banners.
     */
    let notificationTable = null;

    function initNotificationTable() {
        if (notificationTable) return;
        notificationTable = $('#notificationTable').DataTable({
            searching: false,
            paging: false,
            info: false,
            responsive: true,
            scrollY: "60vh",
            scrollCollapse: true,
            ajax: {
                url: '/api/notifications/all',
                dataSrc: resp => (resp.success ? resp.notifications : [])
            },
            columns: [
                {
                    data: 'type',
                    render: v => {
                        const map = {
                            info: 'badge status-info',
                            warning: 'badge status-warning',
                            maintenance: 'badge',
                            critical: 'badge status-critical'
                        };
                        return `<span class="${map[v] || 'badge'}">${v}</span>`;
                    }
                },
                { data: 'title', render: v => v || '—' },
                {
                    data: 'message',
                    render: v => v.length > 60 ? v.slice(0, 60) + '…' : v
                },
                { data: 'priority' },
                {
                    data: 'enabled',
                    render: v => v
                        ? '<span class="badge status-pass"><span class="material-icons">check_circle</span><span>Enabled</span></span>'
                        : '<span class="badge status-notrun"><span class="material-icons">cancel</span><span>Disabled</span></span>'
                },
                {
                    data: 'expires_at',
                    render: v => {
                        if (!v) return 'Never';
                        return new Date(v).toLocaleString('en-GB', {
                            day: '2-digit', month: 'short', year: 'numeric',
                            hour: '2-digit', minute: '2-digit'
                        });
                    }
                },
                {
                    data: null,
                    orderable: false,
                    render: () => `
                     <div style="display:flex; gap:10px; justify-content:center;">
                        <button class="edit-notification icon-text">
                            <span class="material-icons">edit_square</span>
                            <span>Edit</span>
                        </button>
                        <button class="delete-notification icon-text">
                            <span class="material-icons">delete</span>
                            <span>Delete</span>
                        </button>
                     </div>`
                }
            ]
        });
    }

    // Initialize when the Notifications tab is opened.
    $('.app-modal-menu .menu-item[data-id="notifications"]').on('click', () => {
        initNotificationTable();
        notificationTable.ajax.reload(null, false);
    });

    const notificationModalOverlay = document.getElementById('notificationModalOverlay');

    safeAddListener(document.getElementById('closeNotificationModal'), 'click', () => {
        notificationModalOverlay.style.display = 'none';
    });

    // Add
    $('#addNotification').on('click', () => {
        $('#notificationForm')[0].reset();
        $('#notificationId').val('');
        $('#notificationType').val('info');
        $('#notificationPriority').val(0);
        $('#notificationEnabled').prop('checked', true);
        $('#notificationPersistent').prop('checked', false);
        $('#notificationModalTitle').text('Add Notification');
        notificationModalOverlay.style.display = 'flex';
    });

    // Edit
    $('#notificationTable').on('click', '.edit-notification', function () {
        const row = notificationTable.row($(this).closest('tr')).data();
        $('#notificationId').val(row.id);
        $('#notificationType').val(row.type);
        $('#notificationTitleInput').val(row.title || '');
        $('#notificationMessage').val(row.message || '');
        $('#notificationPriority').val(row.priority || 0);
        $('#notificationEnabled').prop('checked', !!row.enabled);
        $('#notificationPersistent').prop('checked', !!row.persistent);
        // datetime-local wants "YYYY-MM-DDTHH:MM"
        $('#notificationExpiresAt').val(
            row.expires_at ? row.expires_at.slice(0, 16) : ''
        );
        $('#notificationModalTitle').text('Edit Notification');
        notificationModalOverlay.style.display = 'flex';
    });

    // Save (add or edit)
    $('#notificationForm').on('submit', function (e) {
        e.preventDefault();
        const payload = {
            id: $('#notificationId').val() || undefined,
            type: $('#notificationType').val(),
            title: $('#notificationTitleInput').val().trim(),
            message: $('#notificationMessage').val().trim(),
            priority: parseInt($('#notificationPriority').val(), 10) || 0,
            enabled: $('#notificationEnabled').is(':checked'),
            persistent: $('#notificationPersistent').is(':checked'),
            expires_at: $('#notificationExpiresAt').val() || null
        };

        $.ajax({
            url: '/api/notification',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Save failed');
                    return;
                }
                notificationModalOverlay.style.display = 'none';
                notificationTable.ajax.reload(null, false);
            },
            error: function (err) {
                alert(err.responseJSON?.message || 'Save failed');
            }
        });
    });

    // Delete
    $('#notificationTable').on('click', '.delete-notification', function () {
        const row = notificationTable.row($(this).closest('tr')).data();
        if (!confirm(`Delete notification "${row.title || row.message}"?`)) return;
        $.ajax({
            url: '/api/notification',
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({ id: row.id }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Delete failed');
                    return;
                }
                notificationTable.ajax.reload(null, false);
            },
            error: function (err) {
                alert(err.responseJSON?.message || 'Delete failed');
            }
        });
    });

    /**
     * Auth provider management:
     * DataTable listing + add/edit/test/delete with type-aware config fields.
     * Secret fields are never returned populated (server redacts to
     * "********"); leaving them blank on edit preserves the stored secret.
     */
    const PROVIDER_FIELDS = {
        local:  [],
        ldap:   ["host", "base_dn", "user_attr", "user_dn_tmpl", "bind_dn", "bind_password", "use_ssl"],
        ad:     ["host", "domain", "base_dn", "bind_dn", "bind_password", "use_ssl"],
        radius: ["host", "port", "secret", "dictionary", "nas_identifier"],
        ssh:    ["host", "port"],
        sso:    ["sso_provider"]
    };

    const PROVIDER_LABELS = {
        local: "Local",
        ldap: "LDAP",
        ad: "Active Directory",
        radius: "RADIUS",
        ssh: "SSH",
        sso: "SSO"
    };

    const PROVIDER_SECRET_FIELDS = ["bind_password", "secret"];

    const PROVIDER_FIELD_LABELS = {
        host:           "Host",
        port:           "Port",
        base_dn:        "Base DN",
        user_attr:      "User Attribute",
        user_dn_tmpl:   "User DN Template",
        bind_dn:        "Bind DN",
        bind_password:  "Bind Password",
        use_ssl:        "Use SSL",
        domain:         "Domain",
        secret:         "Shared Secret",
        dictionary:     "Dictionary Path",
        nas_identifier: "NAS Identifier",
        sso_provider:   "SSO Provider"
    };

    function providerFieldLabel(field) {
        // Fall back to a title-cased version of the raw key if unmapped.
        return PROVIDER_FIELD_LABELS[field]
            || field.replace(/_/g, ' ')
                    .replace(/\b\w/g, c => c.toUpperCase());
    }

    let providerTable = null;

    function initProviderTable() {
        if (providerTable) return;
        providerTable = $('#providerTable').DataTable({
            searching: false,
            paging: false,
            info: false,
            responsive: true,
            scrollY: "60vh",
            scrollCollapse: true,
            ajax: {
                url: '/api/providers',
                dataSrc: resp => (resp.success ? resp.providers : [])
            },
            columns: [
                { data: 'id' },
                { data: 'type', render: v => PROVIDER_LABELS[v] || v },
                {
                    data: 'enabled',
                    render: v => v
                        ? '<span class="badge status-pass"><span class="material-icons">check_circle</span><span>Enabled</span></span>'
                        : '<span class="badge status-notrun"><span class="material-icons">cancel</span><span>Disabled</span></span>'
                },
                { data: 'priority' },
                {
                    data: null,
                    orderable: false,
                    render: row => `
                     <div style="display:flex; gap:10px; justify-content:center;">
                        <button class="edit-provider icon-text">
                            <span class="material-icons">edit_square</span>
                            <span>Edit</span>
                        </button>
                        ${row.id === 'local' ? '' : `
                        <button class="delete-provider icon-text">
                            <span class="material-icons">delete</span>
                            <span>Delete</span>
                        </button>`}
                     </div>`
                }
            ]
        });
    }

    // Initialize providers table when its tab is opened.
    $('.app-modal-menu .menu-item[data-id="providers"]').on('click', () => {
        initProviderTable();
        providerTable.ajax.reload(null, false);
    });

    // Build type-specific config inputs with human-friendly labels.
    function renderProviderConfigFields(type, config = {}) {
        const container = $('#providerConfigFields');
        container.empty();
        if (type === 'local') {
            container.append('<p>No configuration is needed for the Local provider.</p>');
            return;
        }

        (PROVIDER_FIELDS[type] || []).forEach(field => {
            const isSecret = PROVIDER_SECRET_FIELDS.includes(field);
            const isBool = field === 'use_ssl';
            const val = config[field] != null ? config[field] : '';
            const label = providerFieldLabel(field);
            let input;
            if (isBool) {
                input = `<div style="display:flex; gap:10px;" data-cfg-bool="${field}">
                    <label>
                        <input type="radio" name="${field}" value="true" ${val === true ? 'checked' : ''}> Yes
                    </label>
                    <label>
                        <input type="radio" name="${field}" value="false" ${val === false || val === '' ? 'checked' : ''}> No
                    </label>
                </div>`;
            } else {
                input = `<input type="${isSecret ? 'password' : 'text'}"
                                data-cfg="${field}"
                                value="${isSecret ? '' : val}"
                                placeholder="${isSecret ? 'leave blank to keep current' : ''}">`;
            }
            container.append(`<label>${label}</label>${input}`);
        });
    }

    // Collect config from the dynamic fields (blanks omitted to keep secrets).
    function collectProviderConfig() {
        const config = {};

        // Text and secret fields.
        $('#providerConfigFields [data-cfg]').each(function () {
            const key = $(this).data('cfg');
            const v = $(this).val();
            if (v !== '') config[key] = v;
        });

        // Boolean (radio) fields.
        $('#providerConfigFields [data-cfg-bool]').each(function () {
            const key = $(this).data('cfg-bool');
            const selected = $(this).find(`input[name="${key}"]:checked`).val();
            if (selected !== undefined) {
                config[key] = (selected === 'true');
            }
        });

        return config;
    }

    // Re-render config fields when the provider type changes.
    $('#providerType').on('change', function () {
        renderProviderConfigFields($(this).val());
    });

    // Add provider.
    $('#addProvider').on('click', () => {
        $('#providerForm')[0].reset();
        $('#providerId').prop('readonly', false);
        $('#providerType').prop('disabled', false).val('ldap');
        $('#providerEnabled').prop('checked', true);
        $('#providerPriority').val(100);
        $('#providerModalTitle').text('Add Provider');
        renderProviderConfigFields('ldap');
        $('#providerModalOverlay').css('display', 'flex');
    });

    safeAddListener(document.getElementById('closeProviderModal'), 'click', () => {
        $('#providerModalOverlay').hide();
    });

    // Edit provider.
    $('#providerTable').on('click', '.edit-provider', function () {
        const row = providerTable.row($(this).closest('tr')).data();
        $('#providerId').val(row.id).prop('readonly', true);
        $('#providerType').val(row.type).prop('disabled', true);
        $('#providerEnabled').prop('checked', !!row.enabled);
        $('#providerPriority').val(row.priority);
        $('#providerModalTitle').text('Edit Provider');
        renderProviderConfigFields(row.type, row.config || {});
        $('#providerModalOverlay').css('display', 'flex');
    });

    // Save provider (add or edit).
    $('#providerForm').on('submit', function (e) {
        e.preventDefault();
        const payload = {
            id: $('#providerId').val().trim(),
            type: $('#providerType').val(),
            enabled: $('#providerEnabled').is(':checked'),
            priority: parseInt($('#providerPriority').val(), 10) || 100,
            config: collectProviderConfig()
        };
        console.log(payload)
        $.ajax({
            url: '/api/provider',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Save failed');
                    return;
                }
                $('#providerModalOverlay').hide();
                providerTable.ajax.reload(null, false);
            },
            error: function (err) {
                alert(err.responseJSON?.message || 'Save failed');
            }
        });
    });

    // Test provider connectivity.
    $('#testProviderBtn').on('click', function () {
        const id = $('#providerId').val().trim();
        if (!id) {
            alert('Save the provider first, then test.');
            return;
        }
        const btn = $(this);
        btn.prop('disabled', true);
        $.ajax({
            url: '/api/provider/test',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ id }),
            success: resp => alert((resp.success ? 'OK: ' : 'FAILED: ') + resp.message),
            error: () => alert('Test failed'),
            complete: () => btn.prop('disabled', false)
        });
    });

    // Delete provider.
    $('#providerTable').on('click', '.delete-provider', function () {
        const row = providerTable.row($(this).closest('tr')).data();
        if (!confirm(`Delete provider "${row.id}"?`)) return;
        $.ajax({
            url: '/api/provider',
            method: 'DELETE',
            contentType: 'application/json',
            data: JSON.stringify({ id: row.id }),
            success: function (resp) {
                if (!resp.success) {
                    alert(resp.message || 'Delete failed');
                    return;
                }
                providerTable.ajax.reload(null, false);
            },
            error: function (err) {
                alert(err.responseJSON?.message || 'Delete failed');
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
            const allApps = Object.values(data);
            const apps = allApps.filter(app => app.is_registered);

            // No apps available
            if (!apps.length) {
                applicationDropdownToggle.innerHTML = `
                    No app available
                `;
                document.getElementById("applicationDropdownMenu").style.display = "none";
                document.getElementById("mainLayoutContent").innerHTML = `
                    <div
                        style="
                            display:flex;
                            flex-direction:column;
                            align-items:center;
                            justify-content:center;
                            height:100%;
                            text-align:center;
                            color:var(--text-secondary);
                            gap:10px;
                        "
                    >
                        <span class="material-icons" style="font-size:64px;">
                            apps_outage
                        </span>
                        <h2>No applications found</h2>
                        <p>No applications are currently registered.</p>
                        ${
                            CURRENT_USERROLE === 'superadmin'
                                ? `
                                <button id="emptyStateAddApplication" class="icon-text">
                                    <span class="material-icons">add</span>
                                    Add Application
                                </button>
                                `
                                : ''
                        }
                    </div>
                `;
                const addAppBtn = document.getElementById('emptyStateAddApplication');
                if (addAppBtn) {
                    addAppBtn.addEventListener('click', () => {

                        // Open Administration modal
                        adminModal.style.display = 'flex';
                
                        // Switch to Applications tab
                        const applicationsTab = adminModal.querySelector(
                            '.app-modal-menu .menu-item[data-id="applications"]'
                        );

                        if (applicationsTab) {
                            applicationsTab.click();
                        }

                        // Open Add Application modal
                        $('#appModalForm')[0].reset();
                        $('#appModalOverlay').css('display', 'flex');
                    });
                }
                document.querySelector(".logger-dock").style.left = "0";
                return;
            }

            // Get current app from URL path
            currentAppUrl = `/${window.location.pathname.split("/")[1]}`;

            // Find selected app from URL, fallback to first app
            const selectedApp = apps.find(app => app.url_prefix === currentAppUrl) || apps[0];

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

            // Redirect from home page to first available app
            if (window.location.pathname === "/home") {
                window.location.href = `${apps[0].url_prefix}`;
                return;
            }

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
     * - Toggles collapse/expand on button click
     * - Persists state to localStorage
     * - Restores state on load
     */
    const mainLayout = document.getElementById("mainLayout");
    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");

    const SIDEBAR_STATE_KEY = "atx.sidebar.collapsed";

    if (sidebar && mainLayout) {

        const expandSidebar = () => {
            sidebar.classList.remove("collapsed");
            mainLayout.classList.add("sidebar-expanded");
            mainLayout.classList.remove("sidebar-collapsed");
        };

        const collapseSidebar = () => {
            sidebar.classList.add("collapsed");
            mainLayout.classList.add("sidebar-collapsed");
            mainLayout.classList.remove("sidebar-expanded");
        };

        const applyState = (collapsed) => {
            if (collapsed) {
                collapseSidebar();
            } else {
                expandSidebar();
            }
        };

        // Restore saved state on load (defaults to expanded)
        const savedCollapsed = localStorage.getItem(SIDEBAR_STATE_KEY) === "true";
        applyState(savedCollapsed);

        // Toggle on button click
        if (sidebarToggle) {
            sidebarToggle.addEventListener("click", () => {
                const willCollapse = !sidebar.classList.contains("collapsed");
                applyState(willCollapse);
                localStorage.setItem(SIDEBAR_STATE_KEY, String(willCollapse));
            });
        }
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