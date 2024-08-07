const withNextra = require('nextra')({
  theme: 'nextra-theme-docs',
  themeConfig: './theme.config.tsx',
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true
  },
  // Ensure this matches your GitHub repo name
  basePath: '/fuseline',
}

// Merge configurations
module.exports = withNextra(nextConfig)