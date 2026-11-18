const { createApp, ref, computed, onMounted, nextTick, watch } = Vue;

createApp({
  setup() {
    // -----------------------------------------------------------------
    // Authentication & State
    // -----------------------------------------------------------------
    const isAuthenticated = ref(false);
    const usernameInput = ref("");
    const passwordInput = ref("");
    const pinInput = ref("");
    const pinError = ref("");
    const loginError = ref("");
    const activeTab = ref("ledger"); // 'ledger' or 'mandals'
    const isLoading = ref(false);

    // Toast notification state
    const toast = ref({
      show: false,
      message: "",
      type: "success", // success, error, info
    });

    const showToast = (message, type = "success") => {
      toast.value = { show: true, message, type };
      setTimeout(() => {
        toast.value.show = false;
      }, 3500);
    };

    // -----------------------------------------------------------------
    // Master Data & Lists
    // -----------------------------------------------------------------
    const issues = ref([]);
    const mandals = ref([]);
    const mandalSummaries = ref([]);
    const availableGps = ref([]);
    const designations = ref([
      "Panchayat Secretary",
      "Sarpanch",
      "Junior Assistant / GPEO",
      "Computer Operator",
      "Other"
    ]);

    // Top KPIs
    const stats = ref({
      total_records: 0,
      total_dsc_count: 0,
      hyp_count: 0,
      proxkey_count: 0,
      total_billed: 0,
      total_collected: 0,
      total_balance: 0,
      collection_rate: 0,
      status_counts: { Pending: 0, Partial: 0, Paid: 0 }
    });

    // -----------------------------------------------------------------
    // Filters State
    // -----------------------------------------------------------------
    const filters = ref({
      mandal: "",
      variant: "",
      status: "",
      search: "",
      fromDate: "",
      toDate: ""
    });

    // -----------------------------------------------------------------
    // Modals & Active Records
    // -----------------------------------------------------------------
    const showIssueModal = ref(false);
    const isEditMode = ref(false);
    const editingIssueId = ref(null);

    // New/Edit Issue Form Model
    const issueForm = ref({
      token_given_date: new Date().toISOString().split("T")[0],
      mandal_name: "",
      custom_mandal: "",
      gram_panchayat_name: "",
      recipient_name: "",
      designation: "Panchayat Secretary",
      phone_number: "",
      token_variant: "HYP",
      dsc_count: 1,
      unit_price: 1500,
      remarks: "",
      // Initial payment
      has_initial_payment: false,
      initial_amount_paid: 0,
      initial_payment_date: new Date().toISOString().split("T")[0],
      initial_payment_mode: "Cash",
      initial_payment_note: "Initial handover payment"
    });

    // Payment Ledger Drawer / Modal State
    const showPaymentModal = ref(false);
    const activeIssue = ref(null);
    const newPayment = ref({
      payment_date: new Date().toISOString().split("T")[0],
      amount_paid: 0,
      payment_mode: "Cash",
      payment_note: ""
    });
    const paymentWarning = ref("");

    // Delete Confirmation Modal State
    const showDeleteModal = ref(false);
    const itemToDelete = ref(null); // { type: 'issue'|'payment'|'stock', id: number, label: string }

    // Stock Inventory State
    const stock = ref({
      total_procured: 0,
      total_issued: 0,
      total_available: 0,
      hyp_procured: 0,
      hyp_issued: 0,
      hyp_available: 0,
      proxkey_procured: 0,
      proxkey_issued: 0,
      proxkey_available: 0,
      total_investment: 0,
      batches: []
    });
    const showStockModal = ref(false);
    const stockForm = ref({
      stock_date: new Date().toISOString().split("T")[0],
      token_variant: "HYP",
      quantity: 10,
      unit_cost: 0,
      supplier_name: "",
      invoice_ref: "",
      notes: ""
    });

    // -----------------------------------------------------------------
    // Currency & Date Formatters (Indian Locale)
    // -----------------------------------------------------------------
    const formatCurrency = (val) => {
      const num = Number(val) || 0;
      return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
      }).format(num);
    };

    const formatDate = (dateStr) => {
      if (!dateStr) return "-";
      const parts = dateStr.split("-");
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return dateStr;
    };

    // -----------------------------------------------------------------
    // Auth Handlers
    // -----------------------------------------------------------------
    const checkAuth = () => {
      const savedToken = sessionStorage.getItem("dsc_auth_token");
      if (savedToken === "admin-authorized-session-key") {
        isAuthenticated.value = true;
      } else {
        isAuthenticated.value = false;
      }
    };

    const login = async () => {
      try {
        const payload = usernameInput.value ? {
          username: usernameInput.value.trim(),
          password: passwordInput.value.trim()
        } : {
          pin: pinInput.value.trim()
        };

        const res = await fetch("/api/auth/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
          sessionStorage.setItem("dsc_auth_token", data.token);
          isAuthenticated.value = true;
          loginError.value = "";
          pinError.value = "";
          passwordInput.value = "";
          showToast("Welcome " + (usernameInput.value || "Admin") + "! Access granted.", "success");
          fetchData();
        } else {
          loginError.value = data.message || "Invalid Username or Password";
          pinError.value = data.message || "Invalid credentials";
        }
      } catch (err) {
        loginError.value = "Failed to connect to server";
      }
    };

    const verifyPin = login;

    const logout = () => {
      sessionStorage.removeItem("dsc_auth_token");
      isAuthenticated.value = false;
      usernameInput.value = "";
      passwordInput.value = "";
      loginError.value = "";
      showToast("Logged out successfully", "info");
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    };

    // -----------------------------------------------------------------
    // API Data Fetching
    // -----------------------------------------------------------------
    const fetchMandals = async () => {
      try {
        const res = await fetch("/api/metadata/mandals", { cache: "no-store" });
        mandals.value = await res.json();
      } catch (err) {
        console.error("Failed to load mandals", err);
      }
    };

    const fetchGps = async (mandalName = "") => {
      try {
        const url = mandalName ? `/api/metadata/gps?mandal=${encodeURIComponent(mandalName)}` : "/api/metadata/gps";
        const res = await fetch(url, { cache: "no-store" });
        availableGps.value = await res.json();
      } catch (err) {
        console.error("Failed to load GPs", err);
      }
    };

    const fetchStats = async () => {
      try {
        const res = await fetch("/api/analytics/stats", { cache: "no-store" });
        stats.value = await res.json();
      } catch (err) {
        console.error("Failed to load stats", err);
      }
    };

    const fetchMandalSummaries = async () => {
      try {
        const res = await fetch("/api/analytics/mandals", { cache: "no-store" });
        mandalSummaries.value = await res.json();
      } catch (err) {
        console.error("Failed to load mandal abstract", err);
      }
    };

    const fetchIssues = async () => {
      isLoading.value = true;
      try {
        const params = new URLSearchParams();
        if (filters.value.mandal) params.append("mandal", filters.value.mandal);
        if (filters.value.variant) params.append("variant", filters.value.variant);
        if (filters.value.status) params.append("status", filters.value.status);
        if (filters.value.search) params.append("search", filters.value.search);
        if (filters.value.fromDate) params.append("from_date", filters.value.fromDate);
        if (filters.value.toDate) params.append("to_date", filters.value.toDate);

        const res = await fetch(`/api/issues?${params.toString()}`, { cache: "no-store" });
        issues.value = await res.json();
      } catch (err) {
        showToast("Error loading distribution records", "error");
      } finally {
        isLoading.value = false;
        nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });
      }
    };

    const fetchStock = async () => {
      try {
        const res = await fetch("/api/stock", { cache: "no-store" });
        stock.value = await res.json();
      } catch (err) {
        console.error("Failed to load stock data", err);
      }
    };

    const fetchData = async () => {
      await Promise.all([fetchMandals(), fetchStats(), fetchIssues(), fetchMandalSummaries(), fetchStock()]);
    };

    const openAddStockModal = () => {
      stockForm.value = {
        stock_date: new Date().toISOString().split("T")[0],
        token_variant: "HYP",
        quantity: 10,
        unit_cost: 0,
        supplier_name: "",
        invoice_ref: "",
        notes: ""
      };
      showStockModal.value = true;
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    };

    const saveStock = async () => {
      const qty = Number(stockForm.value.quantity) || 0;
      if (qty <= 0) {
        showToast("Please enter a valid stock quantity of at least 1", "error");
        return;
      }
      try {
        const res = await fetch("/api/stock", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stock_date: stockForm.value.stock_date,
            token_variant: stockForm.value.token_variant,
            quantity: qty,
            unit_cost: Number(stockForm.value.unit_cost) || 0,
            supplier_name: stockForm.value.supplier_name.trim(),
            invoice_ref: stockForm.value.invoice_ref.trim(),
            notes: stockForm.value.notes.trim() || null
          })
        });
        if (!res.ok) throw new Error("Failed to record inward stock");
        showToast(`Added ${qty} ${stockForm.value.token_variant} tokens to inventory`, "success");
        showStockModal.value = false;
        await Promise.all([fetchStock(), fetchStats()]);
      } catch (err) {
        showToast(err.message || "Failed to add stock", "error");
      }
    };

    const confirmDeleteStock = (batch) => {
      itemToDelete.value = {
        type: "stock",
        id: batch.id,
        label: `Stock Batch #${batch.id} (${batch.quantity} ${batch.token_variant} tokens)`
      };
      showDeleteModal.value = true;
    };

    // -----------------------------------------------------------------
    // Issue CRUD Actions
    // -----------------------------------------------------------------
    const openNewIssueModal = () => {
      isEditMode.value = false;
      editingIssueId.value = null;
      issueForm.value = {
        token_given_date: new Date().toISOString().split("T")[0],
        mandal_name: filters.value.mandal || (mandals.value[0] || ""),
        custom_mandal: "",
        gram_panchayat_name: "",
        recipient_name: "",
        designation: "Panchayat Secretary",
        phone_number: "",
        token_variant: "HYP",
        dsc_count: 1,
        unit_price: 1500,
        remarks: "",
        has_initial_payment: false,
        initial_amount_paid: 0,
        initial_payment_date: new Date().toISOString().split("T")[0],
        initial_payment_mode: "Cash",
        initial_payment_note: "Initial handover payment"
      };
      fetchGps(issueForm.value.mandal_name);
      showIssueModal.value = true;
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    };

    const openEditIssueModal = (issue) => {
      isEditMode.value = true;
      editingIssueId.value = issue.id;
      issueForm.value = {
        token_given_date: issue.token_given_date,
        mandal_name: issue.mandal_name,
        custom_mandal: "",
        gram_panchayat_name: issue.gram_panchayat_name,
        recipient_name: issue.recipient_name,
        designation: issue.designation,
        phone_number: issue.phone_number,
        token_variant: issue.token_variant,
        dsc_count: issue.dsc_count,
        unit_price: issue.unit_price,
        remarks: issue.remarks || "",
        has_initial_payment: false,
        initial_amount_paid: 0,
        initial_payment_date: issue.token_given_date,
        initial_payment_mode: "Cash",
        initial_payment_note: ""
      };
      fetchGps(issue.mandal_name);
      showIssueModal.value = true;
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    };

    const onMandalChangeInForm = () => {
      if (issueForm.value.mandal_name !== "__custom__") {
        fetchGps(issueForm.value.mandal_name);
      }
    };

    const calculatedTotalAmount = computed(() => {
      const count = Number(issueForm.value.dsc_count) || 0;
      const price = Number(issueForm.value.unit_price) || 0;
      return roundTwo(count * price);
    });

    const roundTwo = (num) => Math.round((num + Number.EPSILON) * 100) / 100;

    const saveIssue = async () => {
      const effectiveMandal = issueForm.value.mandal_name === "__custom__" 
        ? issueForm.value.custom_mandal.trim() 
        : issueForm.value.mandal_name.trim();

      if (!effectiveMandal) {
        showToast("Please select or enter a Mandal", "error");
        return;
      }
      if (!issueForm.value.recipient_name.trim()) {
        showToast("Recipient person's name is required", "error");
        return;
      }

      const payload = {
        token_given_date: issueForm.value.token_given_date,
        mandal_name: effectiveMandal,
        gram_panchayat_name: issueForm.value.gram_panchayat_name ? issueForm.value.gram_panchayat_name.trim() : "",
        recipient_name: issueForm.value.recipient_name.trim(),
        designation: issueForm.value.designation,
        phone_number: issueForm.value.phone_number ? issueForm.value.phone_number.trim() : "",
        token_variant: issueForm.value.token_variant,
        dsc_count: Number(issueForm.value.dsc_count) || 1,
        unit_price: Number(issueForm.value.unit_price) || 1500,
        remarks: issueForm.value.remarks.trim() || null,
      };

      if (!isEditMode.value && issueForm.value.has_initial_payment) {
        payload.initial_amount_paid = Number(issueForm.value.initial_amount_paid) || 0;
        payload.initial_payment_date = issueForm.value.initial_payment_date || issueForm.value.token_given_date;
        payload.initial_payment_mode = issueForm.value.initial_payment_mode || "Cash";
        payload.initial_payment_note = issueForm.value.initial_payment_note || "Initial handover payment";
      }

      try {
        let res;
        if (isEditMode.value) {
          res = await fetch(`/api/issues/${editingIssueId.value}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        } else {
          res = await fetch("/api/issues", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        }

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Failed to save record");
        }

        showToast(isEditMode.value ? "Issue record updated successfully" : "DSC token handover recorded successfully", "success");
        showIssueModal.value = false;
        await fetchData();
      } catch (err) {
        showToast(err.message || "An error occurred", "error");
      }
    };

    const confirmDeleteIssue = (issue) => {
      itemToDelete.value = {
        type: "issue",
        id: issue.id,
        label: `${issue.gram_panchayat_name} (${issue.mandal_name}) - ${issue.recipient_name}`
      };
      showDeleteModal.value = true;
    };

    // -----------------------------------------------------------------
    // Payment Ledger Drawer / Modal Actions
    // -----------------------------------------------------------------
    const openPaymentLedger = async (issue) => {
      try {
        // Fetch fresh copy to ensure payments are 100% current
        const res = await fetch(`/api/issues/${issue.id}`, { cache: "no-store" });
        if (!res.ok) throw new Error("Could not load details");
        activeIssue.value = await res.json();

        // Setup default new installment
        newPayment.value = {
          payment_date: new Date().toISOString().split("T")[0],
          amount_paid: activeIssue.value.balance_amount > 0 ? activeIssue.value.balance_amount : 0,
          payment_mode: "Cash",
          payment_note: ""
        };
        paymentWarning.value = "";
        showPaymentModal.value = true;
        nextTick(() => {
          if (window.lucide) window.lucide.createIcons();
        });
      } catch (err) {
        showToast("Failed to open payment ledger", "error");
      }
    };

    const setPaymentAmount = (amt) => {
      newPayment.value.amount_paid = Number(amt);
      validatePaymentAmount();
    };

    const fillFullBalance = () => {
      if (activeIssue.value) {
        newPayment.value.amount_paid = activeIssue.value.balance_amount;
        validatePaymentAmount();
      }
    };

    const validatePaymentAmount = () => {
      if (!activeIssue.value) return;
      const amt = Number(newPayment.value.amount_paid) || 0;
      if (amt > activeIssue.value.balance_amount) {
        paymentWarning.value = `Note: ₹${amt} exceeds the remaining balance of ₹${activeIssue.value.balance_amount}.`;
      } else {
        paymentWarning.value = "";
      }
    };

    const recordPartPayment = async () => {
      if (!activeIssue.value) return;
      const amt = Number(newPayment.value.amount_paid);
      if (!amt || amt <= 0) {
        showToast("Please enter a valid payment amount greater than ₹0", "error");
        return;
      }

      try {
        const res = await fetch(`/api/issues/${activeIssue.value.id}/payments`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            payment_date: newPayment.value.payment_date,
            amount_paid: amt,
            payment_mode: newPayment.value.payment_mode,
            payment_note: newPayment.value.payment_note ? newPayment.value.payment_note.trim() : null
          })
        });

        if (!res.ok) throw new Error("Failed to record payment");

        showToast(`Payment of ₹${amt} recorded successfully`, "success");
        // Reload active issue
        const updatedRes = await fetch(`/api/issues/${activeIssue.value.id}`, { cache: "no-store" });
        activeIssue.value = await updatedRes.json();

        // Reset form
        newPayment.value.amount_paid = activeIssue.value.balance_amount > 0 ? activeIssue.value.balance_amount : 0;
        newPayment.value.payment_note = "";
        paymentWarning.value = "";

        // Refresh main tables & KPIs in background
        fetchStats();
        fetchIssues();
        fetchMandalSummaries();
      } catch (err) {
        showToast(err.message || "Failed to add payment", "error");
      }
    };

    const confirmDeletePayment = (payment) => {
      itemToDelete.value = {
        type: "payment",
        id: payment.id,
        label: `₹${payment.amount_paid} on ${formatDate(payment.payment_date)} (${payment.payment_mode})`
      };
      showDeleteModal.value = true;
    };

    const executeDelete = async () => {
      if (!itemToDelete.value) return;
      try {
        if (itemToDelete.value.type === "issue") {
          const res = await fetch(`/api/issues/${itemToDelete.value.id}`, { method: "DELETE" });
          if (!res.ok) throw new Error("Failed to delete issue");
          showToast("DSC issue record deleted", "info");
        } else if (itemToDelete.value.type === "payment") {
          const res = await fetch(`/api/payments/${itemToDelete.value.id}`, { method: "DELETE" });
          if (!res.ok) throw new Error("Failed to delete payment");
          showToast("Payment installment removed", "info");

          // Refresh active issue if modal is open
          if (activeIssue.value) {
            const updatedRes = await fetch(`/api/issues/${activeIssue.value.id}`, { cache: "no-store" });
            activeIssue.value = await updatedRes.json();
            newPayment.value.amount_paid = activeIssue.value.balance_amount;
          }
        } else if (itemToDelete.value.type === "stock") {
          const res = await fetch(`/api/stock/${itemToDelete.value.id}`, { method: "DELETE" });
          if (!res.ok) throw new Error("Failed to delete stock batch");
          showToast("Stock batch deleted", "info");
        }

        showDeleteModal.value = false;
        itemToDelete.value = null;
        await fetchData();
      } catch (err) {
        showToast(err.message || "Delete operation failed", "error");
      }
    };

    // -----------------------------------------------------------------
    // Filter & Search Helpers
    // -----------------------------------------------------------------
    const resetFilters = () => {
      filters.value = {
        mandal: "",
        variant: "",
        status: "",
        search: "",
        fromDate: "",
        toDate: ""
      };
      fetchIssues();
    };

    const filterByMandalFromAbstract = (mandalName) => {
      filters.value.mandal = mandalName;
      activeTab.value = "ledger";
      fetchIssues();
    };

    // Debounced search watch
    let searchTimer = null;
    watch(() => filters.value.search, () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        fetchIssues();
      }, 300);
    });

    // Re-render icons on tab or list changes
    watch(activeTab, () => {
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    });

    watch(issues, () => {
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    });

    // -----------------------------------------------------------------
    // Export Functions
    // -----------------------------------------------------------------
    const getExportQueryString = () => {
      const params = new URLSearchParams();
      if (filters.value.mandal) params.append("mandal", filters.value.mandal);
      if (filters.value.variant) params.append("variant", filters.value.variant);
      if (filters.value.status) params.append("status", filters.value.status);
      if (filters.value.search) params.append("search", filters.value.search);
      if (filters.value.fromDate) params.append("from_date", filters.value.fromDate);
      if (filters.value.toDate) params.append("to_date", filters.value.toDate);
      return params.toString();
    };

    const exportToExcel = () => {
      const query = getExportQueryString();
      window.location.href = `/api/export/excel?${query}`;
      showToast("Generating comprehensive Excel ledger...", "info");
    };

    const exportToCsv = () => {
      const query = getExportQueryString();
      window.location.href = `/api/export/csv?${query}`;
      showToast("Downloading CSV file...", "info");
    };

    // -----------------------------------------------------------------
    // Lifecycle
    // -----------------------------------------------------------------
    onMounted(() => {
      checkAuth();
      if (isAuthenticated.value) {
        fetchData();
      }
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    });

    return {
      isAuthenticated,
      usernameInput,
      passwordInput,
      loginError,
      login,
      pinInput,
      pinError,
      verifyPin,
      logout,
      activeTab,
      isLoading,
      toast,
      issues,
      mandals,
      availableGps,
      designations,
      stats,
      mandalSummaries,
      filters,
      fetchIssues,
      resetFilters,
      filterByMandalFromAbstract,
      formatCurrency,
      formatDate,
      // Modals
      showIssueModal,
      isEditMode,
      issueForm,
      calculatedTotalAmount,
      openNewIssueModal,
      openEditIssueModal,
      onMandalChangeInForm,
      saveIssue,
      confirmDeleteIssue,
      // Payment Drawer
      showPaymentModal,
      activeIssue,
      newPayment,
      paymentWarning,
      openPaymentLedger,
      setPaymentAmount,
      fillFullBalance,
      validatePaymentAmount,
      recordPartPayment,
      confirmDeletePayment,
      // Delete Modal
      showDeleteModal,
      itemToDelete,
      executeDelete,
      // Stock Inventory
      stock,
      showStockModal,
      stockForm,
      openAddStockModal,
      saveStock,
      confirmDeleteStock,
      // Export
      exportToExcel,
      exportToCsv
    };
  }
}).mount("#app");
