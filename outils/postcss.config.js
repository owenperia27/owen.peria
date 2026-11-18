module.exports = {
  plugins: {
    tailwindcss: { config: __dirname + '/tailwind.config.js' },
    autoprefixer: { overrideBrowserslist: ['defaults', 'safari >= 12', 'ios_saf >= 12'] },
    cssnano: { preset: 'default' },
  },
};
