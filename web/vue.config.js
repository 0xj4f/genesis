const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  // Do not publish source maps with the production bundle.
  productionSourceMap: false,
  devServer: {
    port: 5173,
  },
})
