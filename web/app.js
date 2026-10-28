// Alpine keeps the page in sync with this state.
function deliveryApp() {
  return {
    campus: { locations: [], roads: [], packages: [] },
    positions: {
      mailroom: [100, 65],
      library: [400, 65],
      cafeteria: [100, 220],
      lab: [400, 220],
    },
    actions: [],
    step: 0,
    robot: "mailroom",
    carrying: null,
    timer: null,
    message: "Choose roads and packages, then find a plan.",
    newPackage: { name: "", origin: "", destination: "" },

    async request(path, body) {
      const options =
        body === undefined
          ? {}
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            };
      const response = await fetch(path, options);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Request failed.");
      return result;
    },

    async init() {
      try {
        await this.loadCampus();
        this.newPackage.origin = this.campus.locations[0];
        this.newPackage.destination = this.campus.locations[0];
      } catch (error) {
        this.message = error.message;
      }
    },

    async loadCampus() {
      this.campus = await this.request("/api/data");
    },

    roadClass(origin, destination) {
      const road = this.campus.roads.find(
        (item) => item.origin === origin && item.destination === destination,
      );
      return road && !road.open ? "road closed" : "road";
    },

    async changeRoad(road, open) {
      try {
        await this.request("/api/road", { id: road.id, open });
        this.clearPlan();
        await this.loadCampus();
      } catch (error) {
        this.message = error.message;
        await this.loadCampus();
      }
    },

    async addPackage() {
      try {
        await this.request("/api/package", this.newPackage);
        this.newPackage.name = "";
        this.clearPlan();
        await this.loadCampus();
      } catch (error) {
        this.message = error.message;
      }
    },

    async removePackage(id) {
      try {
        await this.request("/api/delete-package", { id });
        this.clearPlan();
        await this.loadCampus();
      } catch (error) {
        this.message = error.message;
      }
    },

    clearPlan() {
      this.stopPlayback();
      this.actions = [];
      this.resetRobot();
      this.message = "Setup changed. Find a new plan.";
    },

    resetRobot() {
      this.step = 0;
      this.robot = "mailroom";
      this.carrying = null;
    },

    async findPlan() {
      this.clearPlan();
      this.message = "Finding a plan…";
      try {
        const result = await this.request("/api/plan", {});
        this.actions = result.actions;
        if (!result.found) {
          this.message = "No delivery plan exists with these roads.";
        } else if (!this.actions.length) {
          this.message = "No deliveries are needed.";
        } else {
          this.message = `Plan found: ${this.actions.length} steps. Press Next step or Play.`;
        }
      } catch (error) {
        this.message = error.message;
      }
    },

    describe(action) {
      if (action.type === "move")
        return `Move from ${action.from} to ${action.to}`;
      if (action.type === "pickup")
        return `Pick up ${action.package} at ${action.location}`;
      return `Drop off ${action.package} at ${action.location}`;
    },

    nextStep() {
      if (this.step >= this.actions.length) return;
      const action = this.actions[this.step++];
      if (action.type === "move") this.robot = action.to;
      else if (action.type === "pickup") this.carrying = action.package;
      else this.carrying = null;

      if (this.step === this.actions.length) {
        this.stopPlayback();
        this.message = "All packages delivered.";
      } else {
        this.message = `Step ${this.step} of ${this.actions.length}`;
      }
    },

    togglePlayback() {
      if (this.timer) {
        this.stopPlayback();
      } else {
        this.nextStep();
        if (this.step < this.actions.length) {
          this.timer = setInterval(() => this.nextStep(), 900);
        }
      }
    },

    stopPlayback() {
      clearInterval(this.timer);
      this.timer = null;
    },

    restart() {
      this.stopPlayback();
      this.resetRobot();
      this.message = "Plan reset. Press Next step or Play.";
    },
  };
}
