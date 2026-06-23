import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { describe, expect, it } from "vitest";

import CitationCard from "./CitationCard.vue";

describe("CitationCard", () => {
  it("renders filename page and score", () => {
    const wrapper = mount(CitationCard, {
      props: {
        citation: {
          document_id: 7,
          filename: "VPN故障手册.pdf",
          page: 8,
          text: "先检查本地网络。",
          score: 0.9123,
        },
      },
      global: {
        plugins: [ElementPlus],
      },
    });

    expect(wrapper.text()).toContain(
      "VPN故障手册.pdf",
    );
    expect(wrapper.text()).toContain("第 8 页");
    expect(wrapper.text()).toContain("0.912");
  });
});