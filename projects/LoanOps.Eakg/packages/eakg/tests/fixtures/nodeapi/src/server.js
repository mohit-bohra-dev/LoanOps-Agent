const express = require("express");
const Fastify = require("fastify");

const app = express();
const router = express.Router();

function getLoan(req, res) {
  res.json({ id: req.params.id });
}

app.use("/api", router);
router.get("/loans/:id", getLoan);
router.route("/legacy").get(getLoan);
app.post("/webhooks", (req, res) => res.sendStatus(204));
app.get("env"); // must not become a route

const fastify = Fastify();
fastify.get("/health", async () => ({ ok: true }));
fastify.route({
  method: "GET",
  url: "/ready",
  handler: async () => ({ ready: true }),
});
