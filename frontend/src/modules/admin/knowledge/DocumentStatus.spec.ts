import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { describe, expect, it } from "vitest";

import DocumentStatus from "./DocumentStatus.vue";

describe("DocumentStatus", () => {
  it("shows failed state", () => {
    const wrapper = mount(DocumentStatus, {
      props: {
        status: "FAILED",
        error: "PDF parse failed",
      },
      global: {
        plugins: [ElementPlus],
      },
    });

    expect(wrapper.text()).toContain("解析失败");
  });
});