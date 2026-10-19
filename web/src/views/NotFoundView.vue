<template>
  <div class="page-center">
    <div class="card text-center" style="max-width: 400px; width: 100%;">
      <h2>404 // not found</h2>
      <p class="text-muted mt-sm">There is nothing at this address.</p>
      <router-link to="/" class="btn btn-primary btn-block mt-lg">Go home</router-link>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NotFoundView',
};
</script>
