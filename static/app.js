if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}

const revealItems = document.querySelectorAll(".reveal");

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.15 }
);

revealItems.forEach((item) => revealObserver.observe(item));

const recommendationForm = document.getElementById("recommendation-form");
const recommendationOutput = document.getElementById("recommendation-output");
const nutritionFilterForm = document.getElementById("nutrition-filter-form");

function updateList(targetId, items) {
  const target = document.getElementById(targetId);
  if (!target) return;
  target.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

if (recommendationForm && recommendationOutput) {
  recommendationForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(recommendationForm);
    const body = {
      coach: formData.get("coach"),
      mood: formData.get("mood"),
      energy: Number(formData.get("energy")),
      equipment: formData.get("equipment"),
      goal: formData.get("goal"),
      minutes: Number(formData.get("minutes")),
    };

    recommendationOutput.classList.add("loading");

    try {
      const response = await fetch("/api/recommendation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json();

      const topline = recommendationOutput.querySelector(".recommendation-topline");
      if (topline) {
        topline.innerHTML =
          `<span class="mini-label">${payload.coach_role}</span><strong>${payload.coach_name}</strong>`;
      }
      const headline = document.getElementById("rec-headline");
      const tone = document.getElementById("rec-tone");
      const intensity = document.getElementById("rec-intensity");
      const duration = document.getElementById("rec-duration");
      const equipment = document.getElementById("rec-equipment");
      const next = document.getElementById("rec-next");

      if (headline) headline.textContent = payload.headline;
      if (tone) tone.textContent = payload.tone;
      if (intensity) intensity.textContent = payload.intensity;
      if (duration) duration.textContent = `${payload.duration} min`;
      if (equipment) equipment.textContent = payload.equipment;
      if (next) next.textContent = payload.next_step;

      updateList("rec-blocks", payload.blocks || []);
      updateList("rec-principles", payload.principles || []);
    } catch (error) {
      const headline = document.getElementById("rec-headline");
      if (headline) {
        headline.textContent = "Recommendation temporarily unavailable";
      }
    } finally {
      recommendationOutput.classList.remove("loading");
    }
  });
}

function renderFoods(items) {
  const target = document.getElementById("food-results");
  if (!target) return;
  target.innerHTML = "";
  items.forEach((food) => {
    const article = document.createElement("article");
    article.className = "catalog-card";
    article.innerHTML = `
      <span class="mini-label">${food.unit}</span>
      <strong>${food.name}</strong>
      <div class="catalog-macros">${food.calories} kcal • P ${food.protein} • C ${food.carbs} • F ${food.fats}</div>
      <p>${(food.tags || []).join(", ")}</p>
    `;
    target.appendChild(article);
  });
}

function renderRecipes(items) {
  const target = document.getElementById("recipe-results");
  if (!target) return;
  target.innerHTML = "";
  items.forEach((recipe) => {
    const article = document.createElement("article");
    article.className = "catalog-card recipe-card";
    const ingredients = (recipe.ingredients || []).map((item) => `<li>${item}</li>`).join("");
    article.innerHTML = `
      <span class="mini-label">${recipe.meal_type}</span>
      <strong>${recipe.name}</strong>
      <div class="catalog-macros">${recipe.calories} kcal • P ${recipe.protein} • C ${recipe.carbs} • F ${recipe.fats}</div>
      <p>${recipe.benefit}</p>
      <ul class="bullet-list slim">${ingredients}</ul>
    `;
    target.appendChild(article);
  });
}

if (nutritionFilterForm) {
  nutritionFilterForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(nutritionFilterForm);
    const params = new URLSearchParams({
      goal: String(formData.get("goal") || "all"),
      meal_type: String(formData.get("meal_type") || "all"),
      q: String(formData.get("q") || ""),
    });

    try {
      const response = await fetch(`/api/nutrition?${params.toString()}`);
      const payload = await response.json();
      renderFoods(payload.foods || []);
      renderRecipes(payload.recipes || []);
    } catch (error) {
      // Keep current results if the request fails.
    }
  });
}
