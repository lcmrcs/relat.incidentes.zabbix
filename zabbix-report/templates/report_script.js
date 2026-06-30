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
        const rows = document.querySelectorAll("#incidents-table tbody tr");
        const rowData = Array.from(rows).map((row) => ({
            row,
            date: parseDate(row.children[0].textContent),
            timestamp: Number(row.dataset.timestamp) || 0,
            ageSeconds: Number(row.dataset.ageSeconds) || 0,
            ageLabel: row.dataset.ageLabel || "-",
            unitCode: row.dataset.unitCode,
            equipment: row.dataset.equipment,
            status: row.dataset.status,
            statusRank: statusRank[row.dataset.status] ?? 0,
            unit: row.dataset.unit,
            host: row.dataset.host,
            severity: row.dataset.severity,
            severityRank: severityRank[row.dataset.severity] ?? 0,
            incident: row.dataset.incident,
            incidentType: row.dataset.incidentType,
            resolvedAt: row.querySelector("[data-details]")?.dataset.resolvedAt || "-",
            eventid: row.querySelector("[data-details]")?.dataset.eventid || "",
            searchText: [
                row.dataset.unitCode,
                row.dataset.unit,
                row.dataset.host,
                row.dataset.equipment,
                row.dataset.incident,
                row.dataset.incidentType,
                row.dataset.severity,
                row.dataset.status,
            ].join(" ").toLowerCase(),
        }));
        const status = document.getElementById("filter-status");
        const unitSearch = document.getElementById("unit-search");
        const globalSearch = document.getElementById("global-search");
        const clearFilters = document.getElementById("clear-filters");
        const downloadFiltered = document.getElementById("download-filtered");
        const exportPdfButton = document.getElementById("export-pdf");
        const tableEmpty = document.getElementById("table-empty");
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
        let appliedSortKey = "";
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
            if (item.severity === "Desastre" || item.ageSeconds >= 2592000) {
                return { label: "Crítica", rank: 3, className: "critica" };
            }

            if (item.severity === "Alta" || item.ageSeconds >= 604800) {
                return { label: "Alta", rank: 2, className: "alta" };
            }

            if (item.severity === "Média" || item.ageSeconds >= 86400) {
                return { label: "Média", rank: 1, className: "media" };
            }

            return { label: "Normal", rank: 0, className: "normal" };
        }

        rowData.forEach((item) => {
            const priority = getPriority(item);
            const cell = item.row.querySelector("[data-priority-cell]");
            const detailsButton = item.row.querySelector("[data-details]");

            item.priority = priority.label;
            item.priorityRank = priority.rank;
            item.priorityClass = priority.className;
            item.searchText = `${item.searchText} ${priority.label.toLowerCase()}`;

            if (cell) {
                const badge = document.createElement("span");

                badge.className = `priority-badge ${priority.className}`;
                badge.textContent = priority.label;
                cell.replaceChildren(badge);
            }

            if (detailsButton) {
                detailsButton.dataset.priority = priority.label;
            }
        });

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
                    isAgeInRange(item.ageSeconds, filters.ageRange)) &&
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
                        if (isAgeInRange(item.ageSeconds, range)) {
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
            let visible = 0;
            const visibleAges = [];
            const visibleItems = [];
            const nowSeconds = Date.now() / 1000;
            const filters = getPreparedFilters();

            rowData.forEach((item) => {
                const matches = rowMatchesPrepared(item, filters);

                if (item.row.hidden === matches) {
                    item.row.hidden = !matches;
                }

                if (matches) {
                    visible += 1;
                    visibleItems.push(item);

                    if (item.timestamp) {
                        visibleAges.push(Math.max(0, nowSeconds - item.timestamp));
                    }
                }
            });

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

            applySort();
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

        function getVisibleRows() {
            const filters = getPreparedFilters();

            return rowData.filter((item) => rowMatchesPrepared(item, filters));
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

        function applySort() {
            if (!tableBody) {
                return;
            }

            const cacheKey = `${activeSort.key}:${activeSort.direction}`;

            if (appliedSortKey === cacheKey) {
                return;
            }

            const sortedRows = getSortedRows();
            const fragment = document.createDocumentFragment();

            sortedRows.forEach((item) => {
                fragment.appendChild(item.row);
            });

            tableBody.appendChild(fragment);
            appliedSortKey = cacheKey;
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
                "Tempo offline",
                "Resolvido em",
                "Evento",
            ];
            const lines = [
                headers.map(sanitizeCsvValue).join(";"),
                ...visibleItems.map((item) => [
                    item.row.children[0].textContent.trim(),
                    item.unitCode,
                    item.unit,
                    item.status,
                    item.host,
                    item.equipment,
                    item.incidentType,
                    item.incident,
                    item.severity,
                    item.priority,
                    item.ageLabel,
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
            document.body.classList.add("pdf-exporting");

            window.setTimeout(() => {
                window.print();
            }, 120);

            window.setTimeout(() => {
                document.body.classList.remove("pdf-exporting");
            }, 1200);
        }

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
            agePill.textContent = `Offline: ${button.dataset.ageLabel || "-"}`;
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

            dialog.showModal();
        });

        document.querySelector("[data-modal-close]").addEventListener("click", () => {
            dialog.close();
        });

        if (zabbixDialog && zabbixOpenButton && zabbixCloseButton) {
            zabbixOpenButton.addEventListener("click", () => {
                zabbixDialog.showModal();
            });

            zabbixCloseButton.addEventListener("click", () => {
                zabbixDialog.close();
            });
        }

        if (confeaDialog && confeaOpenButton && confeaCloseButton) {
            confeaOpenButton.addEventListener("click", () => {
                confeaDialog.showModal();
            });

            confeaCloseButton.addEventListener("click", () => {
                confeaDialog.close();
            });
        }
