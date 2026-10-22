(() => {
  const bt = { requests: 0, names: [], disconnects: [], writes: [], mode: "wwr", cancelNext: false, delay: 30, chooserDelay: 0, nameIdx: 0 };
  window.__bt = bt;
  const names = ["MockPrinter A", "MockPrinter B", "MockPrinter C"];
  const makeChar = (devName) => {
    const rec = (method) => async (v) => {
      bt.writes.push({ dev: devName, method, bytes: Array.from(new Uint8Array(v.buffer ? v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength) : v)) });
      await new Promise((r) => setTimeout(r, bt.delay));
    };
    const c = { properties: { write: true, writeWithoutResponse: bt.mode === "wwr" }, writeValue: rec("writeValue") };
    if (bt.mode === "wwr") c.writeValueWithoutResponse = rec("writeValueWithoutResponse");
    if (bt.mode === "wwr" || bt.mode === "wr") c.writeValueWithResponse = rec("writeValueWithResponse");
    return c;
  };
  Object.defineProperty(Navigator.prototype, "bluetooth", {
    configurable: true,
    get() {
      return {
        requestDevice: async () => {
          bt.requests += 1;
          if (bt.chooserDelay) await new Promise((r) => setTimeout(r, bt.chooserDelay));
          if (bt.cancelNext) { bt.cancelNext = false; throw new DOMException("User cancelled the requestDevice() chooser.", "NotFoundError"); }
          const name = names[bt.nameIdx++ % names.length];
          bt.names.push(name);
          const dev = new EventTarget();
          dev.name = name;
          const gatt = {
            connected: false,
            connect: async () => { gatt.connected = true; return { getPrimaryServices: async () => [{ getCharacteristics: async () => [makeChar(name)] }] }; },
            disconnect: () => { bt.disconnects.push(name); gatt.connected = false; setTimeout(() => dev.dispatchEvent(new Event("gattserverdisconnected")), 0); },
          };
          dev.gatt = gatt;
          return dev;
        },
      };
    },
  });
})();
