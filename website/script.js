const tabs = document.querySelectorAll(".tab");
const preview = document.querySelector("#screenPreview");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const nextShot = tab.dataset.shot;

    tabs.forEach((item) => {
      item.classList.remove("is-active");
      item.setAttribute("aria-selected", "false");
    });

    tab.classList.add("is-active");
    tab.setAttribute("aria-selected", "true");
    preview.src = nextShot;
  });
});
