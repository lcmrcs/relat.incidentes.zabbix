        const equipmentButtons = document.querySelectorAll("[data-equipment-filter]");
        const statusButtons = document.querySelectorAll("[data-status-filter]");
        const unitButtons = document.querySelectorAll("[data-unit-filter]");
        const severityButtons = document.querySelectorAll("[data-severity-filter]");
        const ageButtons = document.querySelectorAll("[data-age-filter]");
        const sortButtons = document.querySelectorAll("[data-sort-key]");
        const tableBody = document.querySelector("#incidents-table tbody");
        const severityRank = {
            "Não classificada": 0,
            "Informação": 1,
            "Atenção": 2,
            "Média": 3,
            "Alta": 4,
            "Desastre": 5,
        };
        const statusRank = {
            "Resolvido": 0,
            "Aberto": 1,
        };
        const incidentDataElement = document.getElementById("incident-data");
        const compactIncidentData = incidentDataElement
            ? JSON.parse(incidentDataElement.textContent || "[]")
            : [];
        const rowData = compactIncidentData.map((values) => ({
            dateText: values[0] || "-",
            date: parseDate(values[0] || ""),
            resolvedAt: values[1] || "-",
            status: values[2] || "N/A",
            statusRank: statusRank[values[2]] ?? 0,
            unitCode: values[3] || "-",
            unit: values[4] || "N/A",
            host: values[5] || "N/A",
            equipment: values[6] || "N/A",
            incident: values[7] || "N/A",
            incidentType: values[8] || values[7] || "N/A",
            severity: values[9] || "Não classificada",
            severityRank: severityRank[values[9]] ?? 0,
            timestamp: Number(values[10]) || 0,
            ageSeconds: Number(values[11]) || 0,
            ageLabel: values[12] || "-",
            durationSeconds: Number(values[13]) || 0,
            durationLabel: values[14] || "-",
            openAgeSeconds: Number(values[15]) || 0,
            openAgeLabel: values[16] || "-",
            eventid: values[17] || "",
            searchText: [
                values[3],
                values[4],
                values[5],
                values[6],
                values[7],
                values[8],
                values[9],
                values[2],
            ].join(" ").toLowerCase(),
        }));
        const status = document.getElementById("filter-status");
        const unitSearch = document.getElementById("unit-search");
        const globalSearch = document.getElementById("global-search");
        const clearFilters = document.getElementById("clear-filters");
        const downloadFiltered = document.getElementById("download-filtered");
        const exportPdfButton = document.getElementById("export-pdf");
        const tableEmpty = document.getElementById("table-empty");
        const pagePrevious = document.querySelector("[data-page-previous]");
        const pageNext = document.querySelector("[data-page-next]");
        const pageStatus = document.querySelector("[data-page-status]");
        const pageSizeControl = document.querySelector("[data-page-size]");
        const filterSummaryItems = document.querySelectorAll("[data-filter-summary]");
        const dialog = document.getElementById("incident-dialog");
        const dialogBody = document.getElementById("incident-dialog-body");
        const zabbixDialog = document.getElementById("zabbix-dialog");
        const zabbixOpenButton = document.querySelector("[data-zabbix-open]");
        const zabbixCloseButton = document.querySelector("[data-zabbix-close]");
        const confeaDialog = document.getElementById("confea-dialog");
        const confeaOpenButton = document.querySelector("[data-confea-open]");
        const confeaCloseButton = document.querySelector("[data-confea-close]");
        const themeToggle = document.querySelector("[data-theme-toggle]");
        const presentationToggle = document.querySelector("[data-presentation-toggle]");
        const integrityDialog = document.getElementById("integrity-dialog");
        const integrityOpenButton = document.querySelector("[data-integrity-open]");
        const integrityCloseButton = document.querySelector("[data-integrity-close]");
        const scrollButtons = document.querySelectorAll("[data-scroll-target]");
        const activeFilters = {
            equipment: "all",
            status: "all",
            unit: "all",
            severity: "all",
            age: "all",
            incidentType: "all",
        };
        const activeSort = {
            key: "date",
            direction: "desc",
        };
        const reportConfig = window.REPORT_CONFIG || {};
        const zabbixWebUrl = String(reportConfig.zabbixWebUrl || "").replace(/\/+$/, "");
        let unitSearchText = "";
        let globalSearchText = "";
        let unitSearchTimer = null;
        let globalSearchTimer = null;
        let filterFeedbackTimer = null;
        let sortedRowsCache = null;
        let sortedRowsCacheKey = "";
        let pageSize = 100;
        let currentPage = 1;
        let filteredRows = [];
        let printExpanded = false;
        let lastDialogTrigger = null;
        function getStoredPreference(key, fallback = "") {
            try {
                return window.localStorage?.getItem(key) || fallback;
            } catch {
                return fallback;
            }
        }

        function setStoredPreference(key, value) {
            try {
                window.localStorage?.setItem(key, value);
            } catch {
                // O relatório continua funcional mesmo se o navegador bloquear storage.
            }
        }

        const savedTheme = getStoredPreference("zabbix-report-theme", "light");
        const savedPresentation =
            getStoredPreference("zabbix-report-presentation") === "true";
        const ageFilterValues = Array.from(ageButtons)
            .map((button) => button.dataset.ageFilter)
            .filter((value) => value !== "all");
        const ageRangeCache = new Map();

        function setTheme(theme) {
            const isDark = theme === "dark";

            document.body.classList.toggle("theme-dark", isDark);

            if (themeToggle) {
                const symbol = themeToggle.querySelector("[data-theme-symbol]");
                const label = themeToggle.querySelector("[data-theme-label]");

                if (symbol) {
                    symbol.textContent = isDark ? "☀" : "☾";
                }

                if (label) {
                    label.textContent = isDark ? "Modo solar" : "Modo lunar";
                }

                themeToggle.classList.toggle("active", isDark);
            }

            setStoredPreference("zabbix-report-theme", isDark ? "dark" : "light");
        }

        function setPresentationMode(enabled) {
            document.body.classList.toggle("presentation-mode", enabled);

            if (presentationToggle) {
                presentationToggle.textContent = enabled ? "Modo completo" : "Modo apresentação";
                presentationToggle.classList.toggle("active", enabled);
            }

            setStoredPreference("zabbix-report-presentation", String(enabled));
        }

        setTheme(savedTheme);
        setPresentationMode(savedPresentation);

        if (themeToggle) {
            themeToggle.addEventListener("click", () => {
                setTheme(document.body.classList.contains("theme-dark") ? "light" : "dark");
            });
        }

        if (presentationToggle) {
            presentationToggle.addEventListener("click", () => {
                setPresentationMode(!document.body.classList.contains("presentation-mode"));
            });
        }

        scrollButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const target = document.querySelector(button.dataset.scrollTarget);

                if (!target) {
                    return;
                }

                if (document.body.classList.contains("presentation-mode")) {
                    setPresentationMode(false);
                }

                target.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
            });
        });

        function buildZabbixEventUrl(eventid) {
            if (!zabbixWebUrl || !eventid) {
                return "";
            }

            return `${zabbixWebUrl}/tr_events.php?eventid=${encodeURIComponent(eventid)}`;
        }

        function parseDate(value) {
            const [datePart, timePart = "00:00"] = value.trim().split(" ");
            const [day, month, year] = datePart.split("/").map(Number);
            const [hour, minute] = timePart.split(":").map(Number);

            return new Date(year, month - 1, day, hour, minute).getTime();
        }

        function formatAge(seconds) {
            if (!seconds || seconds <= 0) {
                return "0h";
            }

            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);

            if (days) {
                return `${days}d ${hours}h`;
            }

            if (hours) {
                return `${hours}h ${minutes}min`;
            }

            return `${minutes}min`;
        }

        function getPriority(item) {
            if (item.status !== "Aberto") {
                return { label: "Encerrada", rank: 0, className: "normal" };
            }

            if (item.severity === "Desastre" || item.openAgeSeconds >= 2592000) {
                return { label: "Crítica", rank: 3, className: "critica" };
            }

            if (item.severity === "Alta" || item.openAgeSeconds >= 604800) {
                return { label: "Alta", rank: 2, className: "alta" };
            }

            if (item.severity === "Média" || item.openAgeSeconds >= 86400) {
                return { label: "Média", rank: 1, className: "media" };
            }

            return { label: "Normal", rank: 0, className: "normal" };
        }

        rowData.forEach((item) => {
            const priority = getPriority(item);

            item.priority = priority.label;
            item.priorityRank = priority.rank;
            item.priorityClass = priority.className;
            item.searchText = `${item.searchText} ${priority.label.toLowerCase()}`;
        });

        function normalizeClassName(value) {
            return String(value || "")
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .replace(/\s+/g, "-")
                .toLowerCase();
        }

        function appendTextCell(row, value, className = "") {
            const cell = document.createElement("td");

            cell.className = className;
            cell.textContent = value || "-";
            row.appendChild(cell);
            return cell;
        }

        function createIncidentRow(item) {
            const row = document.createElement("tr");
            const statusCell = document.createElement("td");
            const statusBadge = document.createElement("span");
            const severityCell = document.createElement("td");
            const severityBadge = document.createElement("span");
            const priorityCell = document.createElement("td");
            const priorityBadge = document.createElement("span");
            const detailsCell = document.createElement("td");
            const detailsButton = document.createElement("button");

            appendTextCell(row, item.dateText, "table-date");
            appendTextCell(row, item.unitCode, "table-code");
            appendTextCell(row, item.unit, "table-unit");

            statusBadge.className = `status-badge ${normalizeClassName(item.status)}`;
            statusBadge.textContent = item.status;
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);

            appendTextCell(row, item.equipment, "table-equipment");
            appendTextCell(row, item.incident, "table-incident");

            severityBadge.className = `severity ${normalizeClassName(item.severity)}`;
            severityBadge.textContent = item.severity;
            severityCell.appendChild(severityBadge);
            row.appendChild(severityCell);

            priorityBadge.className = `priority-badge ${item.priorityClass}`;
            priorityBadge.textContent = item.priority;
            priorityCell.appendChild(priorityBadge);
            row.appendChild(priorityCell);

            detailsButton.className = "details-button";
            detailsButton.type = "button";
            detailsButton.textContent = "Abrir";
            detailsButton.dataset.details = "";
            detailsButton.dataset.date = item.dateText;
            detailsButton.dataset.resolvedAt = item.resolvedAt;
            detailsButton.dataset.status = item.status;
            detailsButton.dataset.unitCode = item.unitCode;
            detailsButton.dataset.unit = item.unit;
            detailsButton.dataset.host = item.host;
            detailsButton.dataset.equipment = item.equipment;
            detailsButton.dataset.incident = item.incident;
            detailsButton.dataset.incidentType = item.incidentType;
            detailsButton.dataset.severity = item.severity;
            detailsButton.dataset.priority = item.priority;
            detailsButton.dataset.ageLabel = item.ageLabel;
            detailsButton.dataset.durationLabel = item.durationLabel;
            detailsButton.dataset.openAgeLabel = item.openAgeLabel;
            detailsButton.dataset.eventid = item.eventid;
            detailsCell.appendChild(detailsButton);
            row.appendChild(detailsCell);
            return row;
        }

        function renderIncidentRows(items) {
            if (!tableBody) {
                return;
            }

            const fragment = document.createDocumentFragment();
            items.forEach((item) => fragment.appendChild(createIncidentRow(item)));
            tableBody.replaceChildren(fragment);
        }

        function renderCurrentPage() {
            const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));

            currentPage = Math.min(Math.max(1, currentPage), totalPages);
            const start = (currentPage - 1) * pageSize;
            const pageItems = filteredRows.slice(start, start + pageSize);

            renderIncidentRows(pageItems);
            if (pageStatus) {
                pageStatus.textContent =
                    `Página ${currentPage} de ${totalPages} · ${filteredRows.length} registros`;
            }
            if (pagePrevious) {
                pagePrevious.disabled = currentPage <= 1;
            }
            if (pageNext) {
                pageNext.disabled = currentPage >= totalPages;
            }
        }

        function addCount(map, key) {
            map.set(key, (map.get(key) || 0) + 1);
        }

        function parseAgeRange(value) {
            if (value === "all") {
                return null;
            }

            if (ageRangeCache.has(value)) {
                return ageRangeCache.get(value);
            }

            const [minValue, maxValue] = String(value).split("-");

            const range = {
                min: Number(minValue) || 0,
                max: maxValue ? Number(maxValue) : Infinity,
            };

            ageRangeCache.set(value, range);

            return range;
        }

        function isAgeInRange(ageSeconds, range) {
            if (!range) {
                return true;
            }

            return ageSeconds >= range.min && ageSeconds < range.max;
        }

        function getPreparedFilters(overrides = {}) {
            const age = overrides.age ?? activeFilters.age;

            return {
                equipment: overrides.equipment ?? activeFilters.equipment,
                status: overrides.status ?? activeFilters.status,
                unit: overrides.unit ?? activeFilters.unit,
                severity: overrides.severity ?? activeFilters.severity,
                age,
                ageRange: parseAgeRange(age),
                incidentType:
                    overrides.incidentType ?? activeFilters.incidentType,
                searchText: globalSearchText,
            };
        }

        function rowMatchesPrepared(item, filters) {
            return (
                (filters.equipment === "all" ||
                    item.equipment === filters.equipment) &&
                (filters.status === "all" ||
                    item.status === filters.status) &&
                (filters.unit === "all" ||
                    item.unit === filters.unit) &&
                (filters.severity === "all" ||
                    item.severity === filters.severity) &&
                (filters.incidentType === "all" ||
                    item.incidentType === filters.incidentType) &&
                (filters.age === "all" ||
                    (item.status === "Aberto" &&
                    isAgeInRange(item.openAgeSeconds, filters.ageRange))) &&
                (!filters.searchText ||
                    item.searchText.includes(filters.searchText))
            );
        }

        function rowMatches(item, overrides = {}) {
            return rowMatchesPrepared(item, getPreparedFilters(overrides));
        }

        function showFilterFeedback() {
            document.body.classList.remove("filter-feedback");
            window.clearTimeout(filterFeedbackTimer);

            window.requestAnimationFrame(() => {
                document.body.classList.add("filter-feedback");
                filterFeedbackTimer = window.setTimeout(() => {
                    document.body.classList.remove("filter-feedback");
                }, 820);
            });
        }

        function getCountScope() {
            const counts = {
                equipment: new Map([["all", 0]]),
                status: new Map([["all", 0]]),
                unit: new Map([["all", 0]]),
                severity: new Map([["all", 0]]),
                age: new Map([["all", 0]]),
            };
            const scopes = {
                equipment: getPreparedFilters({ equipment: "all" }),
                status: getPreparedFilters({ status: "all" }),
                unit: getPreparedFilters({ unit: "all" }),
                severity: getPreparedFilters({ severity: "all" }),
                age: getPreparedFilters({ age: "all" }),
            };
            const ageRanges = ageFilterValues.map((value) => ({
                value,
                range: parseAgeRange(value),
            }));

            rowData.forEach((item) => {
                if (rowMatchesPrepared(item, scopes.equipment)) {
                    addCount(counts.equipment, "all");
                    addCount(counts.equipment, item.equipment);
                }

                if (rowMatchesPrepared(item, scopes.status)) {
                    addCount(counts.status, "all");
                    addCount(counts.status, item.status);
                }

                if (rowMatchesPrepared(item, scopes.unit)) {
                    addCount(counts.unit, "all");
                    addCount(counts.unit, item.unit);
                }

                if (rowMatchesPrepared(item, scopes.severity)) {
                    addCount(counts.severity, "all");
                    addCount(counts.severity, item.severity);
                }

                if (rowMatchesPrepared(item, scopes.age)) {
                    addCount(counts.age, "all");

                    ageRanges.forEach(({ value, range }) => {
                        if (item.status === "Aberto" &&
                            isAgeInRange(item.openAgeSeconds, range)) {
                            addCount(counts.age, value);
                        }
                    });
                }
            });

            return counts;
        }

        function updateButtonCounts(buttons, dataName, countMap, options = {}) {
            buttons.forEach((button) => {
                const value = button.dataset[dataName];
                const count = countMap.get(value) || 0;
                const counter = button.querySelector(".filter-count");
                const label = (
                    button.querySelector("span:first-child")?.textContent || ""
                ).toLowerCase();
                const searchMiss =
                    options.search &&
                    value !== "all" &&
                    !label.includes(options.search);

                if (counter) {
                    const nextText = String(count);

                    if (counter.textContent !== nextText) {
                        counter.textContent = nextText;
                    }
                }

                button.classList.toggle(
                    "empty",
                    Boolean(options.search) && searchMiss && value !== "all"
                );
                button.classList.toggle(
                    "zero",
                    count === 0 && value !== "all"
                );
            });
        }

        function updateFilters() {
            const visibleAges = [];
            const nowSeconds = Date.now() / 1000;
            const filters = getPreparedFilters();
            const visibleItems = getSortedRows().filter((item) =>
                rowMatchesPrepared(item, filters)
            );
            const visible = visibleItems.length;

            visibleItems.forEach((item) => {
                if (item.status === "Aberto" && item.timestamp) {
                    visibleAges.push(Math.max(0, nowSeconds - item.timestamp));
                }
            });
            filteredRows = visibleItems;
            currentPage = 1;
            renderCurrentPage();

            equipmentButtons.forEach((button) => {
                button.classList.toggle(
                    "active",
                    button.dataset.equipmentFilter === activeFilters.equipment
                );
            });

            statusButtons.forEach((button) => {
                button.classList.toggle(
                    "active",
                    button.dataset.statusFilter === activeFilters.status
                );
            });

            unitButtons.forEach((button) => {
                button.classList.toggle(
                    "active",
                    button.dataset.unitFilter === activeFilters.unit
                );
            });

            severityButtons.forEach((button) => {
                button.classList.toggle(
                    "active",
                    button.dataset.severityFilter === activeFilters.severity
                );
            });

            ageButtons.forEach((button) => {
                button.classList.toggle(
                    "active",
                    button.dataset.ageFilter === activeFilters.age
                );
            });

            const counts = getCountScope();

            updateSortButtons();
            updateButtonCounts(equipmentButtons, "equipmentFilter", counts.equipment);
            updateButtonCounts(statusButtons, "statusFilter", counts.status);
            updateButtonCounts(severityButtons, "severityFilter", counts.severity);
            updateButtonCounts(ageButtons, "ageFilter", counts.age);
            updateButtonCounts(
                unitButtons,
                "unitFilter",
                counts.unit,
                { search: unitSearchText }
            );

            if (status) {
                const nextStatus = `Exibindo: ${visible}`;

                if (status.textContent !== nextStatus) {
                    status.textContent = nextStatus;
                }
            }

            if (tableEmpty) {
                tableEmpty.hidden = visible !== 0;
            }

            updateFilteredSummary(visible, visibleItems, visibleAges);
        }

        function updateFilteredSummary(total, visibleItems, ages) {
            const oldestAge = ages.length ? Math.max(...ages) : 0;
            const rangeUpTo3 = ages.filter((age) => age < 345600).length;
            const range4To30 = ages.filter((age) => age >= 345600 && age < 2678400).length;
            const rangeOver30 = ages.filter((age) => age >= 2678400).length;
            const priorityHigh = visibleItems.filter((item) => item.priorityRank >= 2).length;

            filterSummaryItems.forEach((item) => {
                const key = item.dataset.filterSummary;

                if (key === "total") {
                    item.textContent = total;
                    return;
                }

                if (key === "oldest") {
                    item.textContent = ages.length ? formatAge(oldestAge) : "-";
                    return;
                }

                if (key === "rangeUpTo3") {
                    item.textContent = rangeUpTo3;
                    return;
                }

                if (key === "range4To30") {
                    item.textContent = range4To30;
                    return;
                }

                if (key === "rangeOver30") {
                    item.textContent = rangeOver30;
                    return;
                }

                if (key === "priorityHigh") {
                    item.textContent = priorityHigh;
                    return;
                }

                item.textContent = 0;
            });
        }

        function compareValues(first, second) {
            if (typeof first === "number" && typeof second === "number") {
                return first - second;
            }

            return String(first || "").localeCompare(
                String(second || ""),
                "pt-BR",
                { numeric: true, sensitivity: "base" }
            );
        }

        function getSortedRows() {
            const cacheKey = `${activeSort.key}:${activeSort.direction}`;

            if (sortedRowsCache && sortedRowsCacheKey === cacheKey) {
                return sortedRowsCache;
            }

            sortedRowsCache = [...rowData].sort((first, second) => {
                const result = compareValues(
                    first[activeSort.key],
                    second[activeSort.key]
                );

                return activeSort.direction === "asc" ? result : -result;
            });
            sortedRowsCacheKey = cacheKey;

            return sortedRowsCache;
        }

        function updateSortButtons() {
            sortButtons.forEach((button) => {
                const isActive = button.dataset.sortKey === activeSort.key;

                button.classList.toggle("active", isActive);
                button.classList.toggle(
                    "asc",
                    isActive && activeSort.direction === "asc"
                );
                button.classList.toggle(
                    "desc",
                    isActive && activeSort.direction === "desc"
                );
            });
        }

        equipmentButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeFilters.equipment = button.dataset.equipmentFilter;
                updateFilters();
            });
        });

        statusButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeFilters.status = button.dataset.statusFilter;
                updateFilters();
            });
        });

        unitButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeFilters.unit = button.dataset.unitFilter;
                updateFilters();
            });
        });

        severityButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeFilters.severity = button.dataset.severityFilter;
                updateFilters();
            });
        });

        ageButtons.forEach((button) => {
            button.addEventListener("click", () => {
                activeFilters.age = button.dataset.ageFilter;
                updateFilters();
            });
        });

        sortButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const key = button.dataset.sortKey;

                if (activeSort.key === key) {
                    activeSort.direction =
                        activeSort.direction === "asc" ? "desc" : "asc";
                } else {
                    activeSort.key = key;
                    activeSort.direction = key === "date" ? "desc" : "asc";
                }

                updateFilters();
            });
        });

        if (pagePrevious) {
            pagePrevious.addEventListener("click", () => {
                currentPage -= 1;
                renderCurrentPage();
            });
        }

        if (pageNext) {
            pageNext.addEventListener("click", () => {
                currentPage += 1;
                renderCurrentPage();
            });
        }

        if (pageSizeControl) {
            pageSizeControl.addEventListener("change", () => {
                pageSize = Number(pageSizeControl.value) || 100;
                currentPage = 1;
                renderCurrentPage();
            });
        }

        document.addEventListener("click", (event) => {
            const button = event.target.closest("[data-quick-status], [data-quick-severity], [data-quick-equipment], [data-quick-unit], [data-quick-search], [data-quick-age], [data-quick-incident-type]");

            if (!button) {
                return;
            }

            if (button.dataset.quickStatus) {
                activeFilters.status = button.dataset.quickStatus;
            }

            if (button.dataset.quickSeverity) {
                activeFilters.severity = button.dataset.quickSeverity;
            }

            if (button.dataset.quickEquipment) {
                activeFilters.equipment = button.dataset.quickEquipment;
            }

            if (button.dataset.quickUnit) {
                activeFilters.unit = button.dataset.quickUnit;
            }

            if (button.dataset.quickAge) {
                activeFilters.age = button.dataset.quickAge;
            }

            if (button.dataset.quickIncidentType) {
                activeFilters.incidentType = button.dataset.quickIncidentType;
            }

            if (button.dataset.quickSearch) {
                globalSearchText = button.dataset.quickSearch.toLowerCase();

                if (globalSearch) {
                    globalSearch.value = button.dataset.quickSearch;
                }
            }

            updateFilters();
            showFilterFeedback();
            document.getElementById("incidents-table")?.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        });

        if (unitSearch) {
            unitSearch.addEventListener("input", () => {
                window.clearTimeout(unitSearchTimer);

                unitSearchTimer = window.setTimeout(() => {
                    unitSearchText = unitSearch.value.trim().toLowerCase();
                    updateFilters();
                }, 120);
            });
        }

        if (globalSearch) {
            globalSearch.addEventListener("input", () => {
                window.clearTimeout(globalSearchTimer);

                globalSearchTimer = window.setTimeout(() => {
                    globalSearchText = globalSearch.value.trim().toLowerCase();
                    updateFilters();
                }, 120);
            });
        }

        if (clearFilters) {
            clearFilters.addEventListener("click", () => {
                activeFilters.equipment = "all";
                activeFilters.status = "all";
                activeFilters.unit = "all";
                activeFilters.severity = "all";
                activeFilters.age = "all";
                activeFilters.incidentType = "all";
                unitSearchText = "";
                globalSearchText = "";

                if (unitSearch) {
                    unitSearch.value = "";
                }

                if (globalSearch) {
                    globalSearch.value = "";
                }

                updateFilters();
            });
        }

        function sanitizeCsvValue(value) {
            const text = String(value ?? "").replace(/\r?\n/g, " ");
            const protectedText = /^[=+\-@]/.test(text) ? `'${text}` : text;

            return `"${protectedText.replace(/"/g, '""')}"`;
        }

        function downloadCsv() {
            const visibleItems = getSortedRows().filter(rowMatches);
            const headers = [
                "Data",
                "Código",
                "Unidade",
                "Status",
                "Host",
                "Equipamento",
                "Tipo de incidente",
                "Incidente",
                "Severidade",
                "Prioridade",
                "Duração total",
                "Idade do passivo aberto",
                "Resolvido em",
                "Evento",
            ];
            const lines = [
                headers.map(sanitizeCsvValue).join(";"),
                ...visibleItems.map((item) => [
                    item.dateText,
                    item.unitCode,
                    item.unit,
                    item.status,
                    item.host,
                    item.equipment,
                    item.incidentType,
                    item.incident,
                    item.severity,
                    item.priority,
                    item.durationLabel,
                    item.openAgeLabel,
                    item.resolvedAt,
                    item.eventid,
                ].map(sanitizeCsvValue).join(";")),
            ];
            const blob = new Blob(
                ["\ufeff", lines.join("\n")],
                { type: "text/csv;charset=utf-8" }
            );
            const link = document.createElement("a");

            link.href = URL.createObjectURL(blob);
            link.download = `zabbix_filtrado_${visibleItems.length}.csv`;
            link.click();
            URL.revokeObjectURL(link.href);
        }

        if (downloadFiltered) {
            downloadFiltered.addEventListener("click", downloadCsv);
        }

        function exportPdf() {
            const printLimit = 5000;

            if (filteredRows.length > printLimit) {
                window.alert(
                    `A impressão foi limitada a ${printLimit.toLocaleString("pt-BR")} registros ` +
                    "para preservar a estabilidade do navegador. Use Baixar CSV para exportar " +
                    "todos os dados filtrados."
                );
                return;
            }

            document.body.classList.add("pdf-exporting");
            document.body.classList.add("print-layout-ready");
            printExpanded = true;
            renderIncidentRows(filteredRows);

            window.setTimeout(() => {
                window.print();
            }, 180);
        }

        window.addEventListener("afterprint", () => {
            document.body.classList.remove("pdf-exporting");
            document.body.classList.remove("print-layout-ready");
            if (printExpanded) {
                printExpanded = false;
                renderCurrentPage();
            }
        });

        if (exportPdfButton) {
            exportPdfButton.addEventListener("click", exportPdf);
        }

        updateFilters();

        document.addEventListener("click", (event) => {
            const button = event.target.closest("[data-details]");

            if (!button) {
                return;
            }

            const zabbixEventUrl = buildZabbixEventUrl(button.dataset.eventid);
            const fields = [
                {
                    label: "Unidade escolar",
                    value: button.dataset.unit,
                    className: "wide identity",
                },
                {
                    label: "Código da unidade",
                    value: button.dataset.unitCode,
                },
                {
                    label: "Host",
                    value: button.dataset.host,
                    className: "wide identity",
                },
                {
                    label: "Equipamento",
                    value: button.dataset.equipment,
                },
                {
                    label: "Tipo de incidente",
                    value: button.dataset.incidentType,
                    className: "wide",
                },
                {
                    label: "Data de abertura",
                    value: button.dataset.date,
                },
                {
                    label: "Evento Zabbix",
                    value: button.dataset.eventid,
                },
                {
                    label: "Severidade",
                    value: button.dataset.severity,
                },
                {
                    label: "Prioridade",
                    value: button.dataset.priority,
                },
            ];

            if (button.dataset.resolvedAt && button.dataset.resolvedAt !== "-") {
                fields.push({
                    label: "Resolvido em",
                    value: button.dataset.resolvedAt,
                });
            }

            fields.push({
                label: "Duração total",
                value: button.dataset.durationLabel || button.dataset.ageLabel,
            });

            if (button.dataset.openAgeLabel && button.dataset.openAgeLabel !== "-") {
                fields.push({
                    label: "Idade do passivo aberto",
                    value: button.dataset.openAgeLabel,
                });
            }

            dialogBody.replaceChildren();

            const heroElement = document.createElement("section");
            const heroTextElement = document.createElement("div");
            const heroEyebrowElement = document.createElement("span");
            const heroTitleElement = document.createElement("h3");
            const heroMetaElement = document.createElement("p");
            const heroActionsElement = document.createElement("div");
            const statusPill = document.createElement("span");
            const agePill = document.createElement("span");
            const eventPill = document.createElement("span");
            const zabbixLink = document.createElement(zabbixEventUrl ? "a" : "span");
            const fieldsGrid = document.createElement("div");

            heroElement.className = "modal-hero";
            heroTextElement.className = "modal-hero-text";
            heroEyebrowElement.className = "modal-eyebrow";
            heroTitleElement.className = "modal-hero-title";
            heroMetaElement.className = "modal-hero-meta";
            heroActionsElement.className = "modal-actions";
            statusPill.className = `modal-pill status-${String(button.dataset.status || "").toLowerCase()}`;
            agePill.className = "modal-pill";
            eventPill.className = "modal-pill";
            zabbixLink.className = zabbixEventUrl ? "modal-zabbix-link" : "modal-zabbix-link disabled";
            fieldsGrid.className = "modal-fields-grid";

            heroEyebrowElement.textContent = "Incidente monitorado";
            heroTitleElement.textContent = button.dataset.incident || "Incidente sem descrição";
            heroMetaElement.textContent = `${button.dataset.host || "-"} • ${button.dataset.unit || "-"}`;
            statusPill.textContent = button.dataset.status || "-";
            agePill.textContent = button.dataset.status === "Aberto"
                ? `Passivo aberto: ${button.dataset.openAgeLabel || "-"}`
                : `Duração: ${button.dataset.durationLabel || "-"}`;
            eventPill.textContent = `Evento: ${button.dataset.eventid || "-"}`;

            if (zabbixEventUrl) {
                zabbixLink.href = zabbixEventUrl;
                zabbixLink.target = "_blank";
                zabbixLink.rel = "noopener noreferrer";
                zabbixLink.textContent = "Abrir no Zabbix";
            } else {
                zabbixLink.textContent = "Link indisponível";
            }

            heroActionsElement.append(statusPill, agePill, eventPill, zabbixLink);
            heroTextElement.append(heroEyebrowElement, heroTitleElement, heroMetaElement);
            heroElement.append(heroTextElement, heroActionsElement);
            dialogBody.append(heroElement, fieldsGrid);

            fields.forEach(({ label, value, className }) => {
                const fieldElement = document.createElement("div");
                const labelElement = document.createElement("div");
                const valueElement = document.createElement("div");

                fieldElement.className = `modal-field ${className || ""}`.trim();
                labelElement.className = "modal-label";
                valueElement.className = "modal-value";
                labelElement.textContent = label;
                valueElement.textContent = value || "-";

                fieldElement.append(labelElement, valueElement);
                fieldsGrid.append(fieldElement);
            });

            lastDialogTrigger = button;
            dialog.showModal();
        });

        document.querySelector("[data-modal-close]").addEventListener("click", () => {
            dialog.close();
        });

        if (zabbixDialog && zabbixOpenButton && zabbixCloseButton) {
            zabbixOpenButton.addEventListener("click", () => {
                lastDialogTrigger = zabbixOpenButton;
                zabbixDialog.showModal();
            });

            zabbixCloseButton.addEventListener("click", () => {
                zabbixDialog.close();
            });
        }

        if (confeaDialog && confeaOpenButton && confeaCloseButton) {
            confeaOpenButton.addEventListener("click", () => {
                lastDialogTrigger = confeaOpenButton;
                confeaDialog.showModal();
            });

            confeaCloseButton.addEventListener("click", () => {
                confeaDialog.close();
            });
        }

        if (integrityDialog && integrityOpenButton && integrityCloseButton) {
            integrityOpenButton.addEventListener("click", () => {
                lastDialogTrigger = integrityOpenButton;
                integrityDialog.showModal();
            });
            integrityCloseButton.addEventListener("click", () => integrityDialog.close());
        }

        [dialog, zabbixDialog, confeaDialog, integrityDialog]
            .filter(Boolean)
            .forEach((modal) => {
                modal.addEventListener("close", () => {
                    lastDialogTrigger?.focus();
                    lastDialogTrigger = null;
                });
            });
