import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "@/layouts/AppLayout.vue";
import { useAuthStore } from "@/modules/auth/store";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () =>
        import("@/modules/auth/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          redirect: "/chat",
        },
        {
          path: "chat",
          component: () =>
            import("@/modules/chat/ChatView.vue"),
        },
        {
          path: "admin/users",
          component: () =>
            import(
              "@/modules/admin/users/UserAdminView.vue"
            ),
          meta: { admin: true },
        },
        {
          path: "admin/knowledge",
          component: () =>
            import(
              "@/modules/admin/knowledge/KnowledgeAdminView.vue"
            ),
          meta: { admin: true },
        },
        {
          path: "admin/evaluation",
          component: () =>
            import(
              "@/modules/evaluation/PromptEvaluationView.vue"
            ),
          meta: { admin: true },
        },
        {
          path: "admin/traces",
          component: () =>
            import(
              "@/modules/traces/TraceView.vue"
            ),
          meta: { admin: true },
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/chat",
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (to.meta.public) {
    if (auth.isAuthenticated) {
      return "/chat";
    }
    return true;
  }

  if (!auth.isAuthenticated) {
    return {
      path: "/login",
      query: { redirect: to.fullPath },
    };
  }

  if (!auth.user) {
    try {
      await auth.loadCurrentUser();
    } catch {
      auth.logout();
      return "/login";
    }
  }

  if (to.meta.admin && !auth.isAdmin) {
    return "/chat";
  }

  return true;
});

window.addEventListener("auth:expired", () => {
  void router.replace("/login");
});

export default router;